import logging

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode, url_has_allowed_host_and_scheme
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings as django_settings
from .models import UserProfile, OTPCode

logger = logging.getLogger(__name__)


def _safe_redirect_target(request, default='/dashboard/'):
    """جلوگیری از Open Redirect: فقط مقصدهای داخلی همین دامنه مجازند."""
    target = request.POST.get('next') or request.GET.get('next') or ''
    if target and url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return default


def _user_role(user):
    try:
        return user.profile.role
    except Exception:
        return ''


def _is_student_dest(url: str) -> bool:
    if not url:
        return False
    prefixes = (
        '/dashboard/payments',
        '/dashboard/registration',
        '/dashboard/schedule',
        '/dashboard/exam',
        '/dashboard/courses',
        '/accounts/register',
    )
    return any(url.startswith(p) for p in prefixes)


def _student_post_login_redirect(request, user):
    """دانشجو را به مرحله بعدی مسیر (شهریه / انتخاب واحد / …) بفرست."""
    from dashboard.onboarding import next_journey_url
    default = next_journey_url(user=user)
    return redirect(_safe_redirect_target(request, default=default))


def login_view(request):
    next_raw = request.GET.get('next') or request.POST.get('next') or ''

    # اگر ادمین لاگین است ولی می‌خواهد مسیر دانشجو را ادامه دهد، خارج شو تا بتواند با کد ملی وارد شود
    if request.user.is_authenticated:
        role = _user_role(request.user)
        if role in ('admin', 'staff') or request.user.is_superuser:
            if _is_student_dest(next_raw) or request.GET.get('as_student') == '1':
                logout(request)
                messages.info(request, 'از حساب مدیریت خارج شدید. با کد ملی دانشجو وارد شوید.')
            else:
                return redirect('/admin/' if role in ('admin', 'staff') or request.user.is_superuser else 'dashboard:dashboard')
        elif role == 'student':
            return _student_post_login_redirect(request, request.user)
        else:
            return redirect(_safe_redirect_target(request))

    if request.method == 'POST':
        from core import captcha
        from core.iran import only_digits, normalize_digits

        # پیش از هر کاری: بدون کپچای درست، رمز اصلاً بررسی نمی‌شود.
        # اگر بعد از authenticate می‌آمد، ربات می‌توانست از تفاوت
        # زمان پاسخ بفهمد رمز درست بوده یا نه.
        if captcha.is_enabled() and not captcha.check(
                request.session, request.POST.get('captcha', '')):
            messages.error(request, 'پاسخ عبارت امنیتی درست نیست. دوباره تلاش کنید.')
            return render(request, 'accounts/login.html', {
                'page_title': 'ورود به سامانه',
                'next': next_raw,
            })

        raw_id = (request.POST.get('national_id') or '').strip()
        digits = only_digits(raw_id)
        # اگر فقط رقم بود → کد ملی؛ وگرنه نام کاربری را دست‌نخورده نگه دار
        # (قبلاً only_digits برای admin2 به «2» تبدیل می‌شد و ورود روی موبایل/دسکتاپ می‌ترکید)
        norm = normalize_digits(raw_id).replace(' ', '').replace('-', '')
        login_id = digits if digits and digits == norm else raw_id
        password = request.POST.get('password')

        user = None
        if login_id and password:
            # ۱) ورود مستقیم با نام کاربری (مثلاً admin / admin2)
            user = authenticate(request, username=login_id, password=password)
            # ۲) ورود با کد ملی ذخیره‌شده در پروفایل
            if user is None and digits:
                profile = (
                    UserProfile.objects
                    .select_related('user')
                    .filter(national_id=digits)
                    .first()
                )
                if profile:
                    user = authenticate(
                        request,
                        username=profile.user.username,
                        password=password,
                    )

        if user:
            user_role = _user_role(user)
            login(request, user)
            messages.success(request, f'خوش آمدید، {user.get_full_name() or user.username}!')
            # اگر مقصد مسیر دانشجویی است، همان را اولویت بده (حتی برای ادمین تست‌کننده)
            dest = _safe_redirect_target(request, default='')
            if user_role == 'student':
                return _student_post_login_redirect(request, user)
            if dest and _is_student_dest(dest):
                return redirect(dest)
            if user_role == 'admin' or user.is_superuser or user_role == 'staff':
                return redirect('/admin/')
            return redirect(dest or '/dashboard/')
        else:
            messages.error(request, 'کد ملی / نام کاربری یا رمز عبور اشتباه است.')

    context = {
        'page_title': 'ورود به سامانه',
        'next': next_raw,
    }
    return render(request, 'accounts/login.html', context)


def logout_view(request):
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    logout(request)
    messages.info(request, 'با موفقیت خارج شدید.')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('/')


def register_view(request):
    from core.iran import only_digits
    pref_nid = only_digits(request.GET.get('nid') or '') or (request.GET.get('nid') or '').strip()
    from_track = request.GET.get('from') == 'track' or bool(pref_nid)

    # ادمین/کارمند لاگین‌شده نباید مانع ساخت حساب دانشجو شود
    if request.user.is_authenticated:
        role = _user_role(request.user)
        try:
            my_nid = (request.user.profile.national_id or request.user.username or '').strip()
        except Exception:
            my_nid = (request.user.username or '').strip()
        same_student = pref_nid and my_nid == pref_nid and role == 'student'
        if same_student:
            from dashboard.onboarding import next_journey_url
            return redirect(next_journey_url(user=request.user))
        if from_track or role in ('admin', 'staff') or request.user.is_superuser:
            logout(request)
            messages.info(
                request,
                'برای ساخت حساب دانشجویی از حساب فعلی خارج شدید. فرم را تکمیل کنید.',
            )
        else:
            return redirect('dashboard:dashboard')

    # پیش‌پر کردن از صفحه پیگیری پذیرش
    pref = {
        'national_id': pref_nid,
        'first_name': '',
        'last_name': '',
        'phone': '',
        'from_track': from_track,
    }
    accepted_app = None
    if pref['national_id']:
        from admissions.models import Application
        accepted_app = (
            Application.objects.filter(national_id=pref['national_id'], status='accepted')
            .select_related('desired_major')
            .order_by('-id')
            .first()
        )
        if accepted_app:
            pref['first_name'] = accepted_app.first_name or ''
            pref['last_name'] = accepted_app.last_name or ''
            pref['phone'] = accepted_app.phone or ''

    if request.method == 'POST':
        from core import captcha
        from core.iran import is_valid_mobile, is_valid_national_id, only_digits
        from admissions.models import Application

        # کپچا اول: ساختن حساب گران‌تر از ورود است و نباید یک ربات
        # بتواند با کد ملی‌های تصادفی جدول کاربران را پر کند.
        if captcha.is_enabled() and not captcha.check(
                request.session, request.POST.get('captcha', '')):
            messages.error(request, 'پاسخ عبارت امنیتی درست نیست. دوباره تلاش کنید.')
            return render(request, 'accounts/register.html', {
                'page_title': 'ثبت‌نام',
                'pref': pref,
                'accepted_app': accepted_app,
            })

        national_id = only_digits(request.POST.get('national_id', ''))
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # هویت از پروندهٔ پذیرش خوانده می‌شود، نه از کیبورد متقاضی.
        # قبلاً پنج فیلد (نام، نام خانوادگی، ایمیل، موبایل، کد ملی) دوباره
        # تایپ می‌شد در حالی که همه در Application موجودند؛ و «دانشکده» و
        # «شماره دانشجویی» را خود کاربر وارد می‌کرد که هیچ‌کدام دادهٔ کاربر نیست.
        src_app = (
            Application.objects.filter(national_id=national_id, status='accepted')
            .select_related('desired_major', 'desired_major__department')
            .order_by('-id')
            .first()
        )
        # اگر پرونده نبود، هویت از خود فرم گرفته می‌شود تا ثبت‌نام مسدود نشود.
        if src_app:
            first_name = (src_app.first_name or '').strip()
            last_name = (src_app.last_name or '').strip()
            email = (src_app.email or '').strip()
            phone = only_digits(src_app.phone or '')
        else:
            first_name = (request.POST.get('first_name') or '').strip()
            last_name = (request.POST.get('last_name') or '').strip()
            email = (request.POST.get('email') or '').strip()
            phone = only_digits(request.POST.get('phone') or '')
        # دانشکده از رشتهٔ پذیرش مشتق می‌شود
        department = ''
        if src_app and src_app.desired_major_id:
            dep = getattr(src_app.desired_major, 'department', None)
            department = getattr(dep, 'name', '') or ''
        # شمارهٔ دانشجویی را موسسه صادر می‌کند؛ تا آن زمان خالی می‌ماند
        student_id = ''

        role = 'student'

        pwd_error = None
        if password1 and password1 == password2:
            try:
                validate_password(password1)
            except ValidationError as e:
                pwd_error = ' '.join(e.messages)

        accepted = src_app is not None

        if not national_id or not password1 or not password2:
            messages.error(request, 'لطفاً کد ملی و رمز عبور را وارد کنید.')
        elif not is_valid_national_id(national_id):
            messages.error(request, 'کد ملی معتبر نیست.')
        elif accepted and phone and not is_valid_mobile(phone):
            messages.error(
                request,
                'شماره موبایل ثبت‌شده در پروندهٔ پذیرش معتبر نیست. با موسسه تماس بگیرید.',
            )
        elif not accepted and getattr(
            django_settings, 'REQUIRE_ACCEPTED_APPLICATION_FOR_SIGNUP', False
        ):
            messages.error(
                request,
                'ثبت‌نام دانشجویی فقط پس از پذیرش نهایی ممکن است. '
                'وضعیت درخواست را از صفحه پیگیری بررسی کنید.',
            )
        elif not accepted and not (first_name and last_name):
            messages.error(request, 'نام و نام خانوادگی را وارد کنید.')
        elif not accepted and not is_valid_mobile(phone):
            messages.error(request, 'شماره موبایل معتبر نیست.')
        elif phone and UserProfile.objects.filter(phone=phone).exists():
            messages.error(request, 'این شماره موبایل قبلاً ثبت‌نام شده است.')
        elif UserProfile.objects.filter(national_id=national_id).exists():
            messages.error(
                request,
                'برای این کد ملی قبلاً حساب ساخته شده است. وارد شوید — '
                'و اگر رمز را به خاطر ندارید، از «فراموشی رمز عبور» '
                'استفاده کنید.')
        elif password1 != password2:
            messages.error(request, 'رمز عبور و تکرار آن یکسان نیستند.')
        elif pwd_error:
            messages.error(request, pwd_error)
        elif User.objects.filter(username=national_id).exists():
            messages.error(request, 'این کد ملی قبلاً ثبت‌نام شده است.')
        else:
            user = User.objects.create_user(
                username=national_id,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
            )
            profile_defaults = {
                'role': role,
                'national_id': national_id,
                'student_id': student_id,
                'department': department,
                'phone': phone,
            }
            app = src_app
            if app and app.desired_major_id:
                profile_defaults['major'] = app.desired_major
            UserProfile.objects.update_or_create(
                user=user,
                defaults=profile_defaults,
            )
            from dashboard.onboarding import ensure_tuition_invoice, sync_profile_from_application
            sync_profile_from_application(user, app)
            login(request, user)
            ensure_tuition_invoice(user)
            if accepted:
                messages.success(
                    request,
                    'حساب کاربری ساخته شد. مرحله بعد: پرداخت شهریه. '
                    'پروفایل و عکس پرسنلی را از صفحه «پروفایل من» تکمیل/بررسی کنید.',
                )
                return redirect('dashboard:student_payments')
            # بدون پروندهٔ پذیرش هنوز رشته و شهریه‌ای نیست؛ اول پروفایل کامل شود
            messages.success(
                request,
                'حساب کاربری ساخته شد. لطفاً پروفایل خود را تکمیل کنید. '
                'پس از تأیید پذیرش، رشته و شهریه به حساب شما اضافه می‌شود.',
            )
            return redirect('accounts:profile')

        # فرم که رد شد، نوشته‌های کاربر نباید پاک شوند
        if not accepted:
            pref.update({
                'national_id': national_id,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
            })

    context = {'page_title': 'ثبت‌نام', 'pref': pref, 'accepted_app': accepted_app}
    return render(request, 'accounts/register.html', context)


@login_required
def profile(request):
    from core.iran import (
        is_valid_mobile, only_digits, parse_gpa, validate_personnel_photo,
    )
    from dashboard.onboarding import get_accepted_application, sync_profile_from_application

    profile_obj, _created = UserProfile.objects.get_or_create(user=request.user)
    sync_profile_from_application(request.user)
    profile_obj.refresh_from_db()

    if request.method == 'POST':
        p = request.POST
        first_name = (p.get('first_name') or '').strip()
        last_name = (p.get('last_name') or '').strip()
        father_name = (p.get('father_name') or '').strip()
        phone = only_digits(p.get('phone', ''))
        phone_emergency = only_digits(p.get('phone_emergency', ''))
        department = (p.get('department') or '').strip()
        bio = (p.get('bio') or '').strip()
        email = (p.get('email') or '').strip()
        gender = (p.get('gender') or '').strip()
        military = (p.get('military') or 'na').strip()
        province = (p.get('province') or '').strip()
        city = (p.get('city') or '').strip()
        address = (p.get('address') or '').strip()
        postal_code = only_digits(p.get('postal_code', ''))
        prev_degree = (p.get('prev_degree') or '').strip()
        prev_major = (p.get('prev_major') or '').strip()
        prev_school = (p.get('prev_school') or '').strip()
        prev_grad_year = only_digits(p.get('prev_grad_year', ''))
        student_id = only_digits(p.get('student_id', '')) or (p.get('student_id') or '').strip()
        hijab_ok = bool(p.get('photo_hijab_confirmed'))
        avatar_file = request.FILES.get('avatar')

        errors = []
        if not first_name or not last_name:
            errors.append('نام و نام خانوادگی الزامی است.')
        if phone and not is_valid_mobile(phone):
            errors.append('شماره موبایل باید ۱۱ رقم و با ۰۹ شروع شود.')
        if phone and UserProfile.objects.filter(phone=phone).exclude(pk=profile_obj.pk).exists():
            errors.append('این شماره موبایل قبلاً ثبت شده است.')
        if postal_code and len(postal_code) not in (0, 10):
            errors.append('کد پستی باید ۱۰ رقم باشد.')
        if gender and gender not in dict(UserProfile.GENDER_CHOICES):
            errors.append('جنسیت نامعتبر است.')
        gpa_val, gpa_err = parse_gpa(p.get('gpa'))
        if gpa_err:
            errors.append(gpa_err)

        if gender == 'female':
            military = 'na'
        effective_gender = gender or profile_obj.gender
        if avatar_file:
            errors.extend(
                validate_personnel_photo(
                    avatar_file,
                    gender=effective_gender,
                    hijab_confirmed=hijab_ok or profile_obj.photo_hijab_confirmed,
                    required=True,
                )
            )
        elif profile_obj.role == 'student' and not profile_obj.avatar:
            errors.append('عکس پرسنلی الزامی است.')
            if effective_gender == 'female' and not (hijab_ok or profile_obj.photo_hijab_confirmed):
                errors.append(
                    'برای بانوان تأیید حجاب کامل در عکس پرسنلی الزامی است.'
                )
        elif effective_gender == 'female' and profile_obj.avatar and not (
            hijab_ok or profile_obj.photo_hijab_confirmed
        ):
            errors.append('برای بانوان تأیید حجاب کامل در عکس پرسنلی الزامی است.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            request.user.first_name = first_name
            request.user.last_name = last_name
            if email != request.user.email:
                request.user.email = email
            request.user.save(update_fields=['first_name', 'last_name', 'email'])

            profile_obj.father_name = father_name
            profile_obj.phone = phone
            profile_obj.phone_emergency = phone_emergency
            profile_obj.department = department
            profile_obj.bio = bio
            profile_obj.gender = gender
            profile_obj.military = military if gender != 'female' else 'na'
            profile_obj.province = province
            profile_obj.city = city
            profile_obj.address = address
            profile_obj.postal_code = postal_code
            profile_obj.prev_degree = prev_degree
            profile_obj.prev_major = prev_major
            profile_obj.prev_school = prev_school
            profile_obj.prev_grad_year = prev_grad_year
            profile_obj.gpa = gpa_val
            profile_obj.student_id = student_id
            if gender == 'female':
                profile_obj.photo_hijab_confirmed = hijab_ok or profile_obj.photo_hijab_confirmed
            else:
                profile_obj.photo_hijab_confirmed = False
            if avatar_file:
                profile_obj.avatar = avatar_file
            profile_obj.save()
            messages.success(request, 'پروفایل با موفقیت به‌روزرسانی شد.')
            return redirect('accounts:profile')

    app = get_accepted_application(profile_obj.national_id or request.user.username)
    context = {
        'profile': profile_obj,
        'application': app,
        'completeness': profile_obj.completeness_percent(),
        'prev_degree_choices': UserProfile.PREV_DEGREE_CHOICES,
        'page_title': 'پروفایل من',
    }
    return render(request, 'accounts/profile.html', context)


# ─────────────────────────────────────────────────────────────────
# بازیابی رمز — انتخاب روش: ایمیل یا پیامک
# ─────────────────────────────────────────────────────────────────
def password_reset_request(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        method = request.POST.get('method', '')  # 'email' یا 'sms'

        # ───── روش ایمیل ─────
        if method == 'email':
            email = request.POST.get('email', '').strip()
            if not email:
                messages.error(request, 'لطفاً آدرس ایمیل را وارد کنید.')
                return render(request, 'accounts/password_reset_request.html',
                              {'page_title': 'بازیابی رمز عبور', 'active_method': 'email'})

            users = User.objects.filter(email__iexact=email, is_active=True)
            if users.exists():
                user = users.first()
                uid   = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(
                    f'/accounts/password-reset/{uid}/{token}/'
                )
                subject = 'بازیابی رمز عبور — موسسه آموزش عالی علامه امینی'
                html_body = render_to_string(
                    'accounts/email/password_reset_email.html',
                    {'user': user, 'reset_url': reset_url},
                )
                plain_body = (
                    f'سلام {user.get_full_name() or user.username}،\n\n'
                    f'برای بازیابی رمز عبور روی لینک زیر کلیک کنید:\n{reset_url}\n\n'
                    f'این لینک ۱ ساعت اعتبار دارد.\n\n'
                    f'اگر این درخواست از شما نیست، این ایمیل را نادیده بگیرید.'
                )
                try:
                    send_mail(
                        subject,
                        plain_body,
                        django_settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        html_message=html_body,
                        fail_silently=False,
                    )
                except Exception:
                    # پیام موفقیت را عوض نمی‌کنیم — وگرنه از روی تفاوت
                    # پاسخ می‌شود فهمید کدام ایمیل در سامانه ثبت است.
                    # ولی خطا باید جایی ثبت شود، وگرنه «ایمیل نمی‌آید»
                    # هیچ ردی در لاگ نمی‌گذارد و قابل عیب‌یابی نیست.
                    logger.exception('ارسال ایمیل بازیابی رمز شکست خورد')
            # user-enumeration prevention
            messages.success(request, 'اگر این ایمیل در سامانه ثبت شده باشد، لینک بازیابی ارسال شد.')
            return redirect('accounts:password_reset_request')

        # ───── روش پیامک ─────
        elif method == 'sms':
            phone = request.POST.get('phone', '').strip()
            if not phone:
                messages.error(request, 'لطفاً شماره موبایل را وارد کنید.')
                return render(request, 'accounts/password_reset_request.html',
                              {'page_title': 'بازیابی رمز عبور', 'active_method': 'sms'})

            # جستجوی کاربر بر اساس شماره موبایل ثبت‌شده در پروفایل
            from accounts.models import UserProfile as UP
            profile_qs = UP.objects.filter(phone=phone).select_related('user')
            if profile_qs.exists() and profile_qs.first().user.is_active:
                user = profile_qs.first().user
                otp = OTPCode.create_for_user(user)

                sms_text = f'کد بازیابی رمز عبور شما: {otp.code}\nاین کد ۱۰ دقیقه اعتبار دارد.'

                from core.sms import can_send_otp, mark_otp_sent, send_otp
                ok, err = can_send_otp(phone, scope='reset')
                if not ok:
                    messages.error(request, err)
                    return render(request, 'accounts/password_reset_request.html',
                                  {'page_title': 'بازیابی رمز عبور', 'active_method': 'sms'})

                sent = send_otp(phone, otp.code, sms_text)
                if not sent:
                    messages.error(request, 'ارسال پیامک ناموفق بود. لطفاً چند لحظه دیگر تلاش کنید.')
                    return render(request, 'accounts/password_reset_request.html',
                                  {'page_title': 'بازیابی رمز عبور', 'active_method': 'sms'})

                mark_otp_sent(phone, scope='reset')
                request.session['otp_phone'] = phone
                messages.success(request, f'کد تأیید به شماره {phone[:4]}****{phone[-3:]} ارسال شد.')
                return redirect('accounts:password_reset_otp')

            # user-enumeration prevention
            messages.success(request, 'اگر این شماره در سامانه ثبت شده باشد، کد تأیید ارسال شد.')
            return redirect('accounts:password_reset_request')

    return render(request, 'accounts/password_reset_request.html',
                  {'page_title': 'بازیابی رمز عبور', 'active_method': ''})


# ─────────────────────────────────────────────────────────────────
# بازیابی رمز با OTP پیامکی — تأیید کد و تنظیم رمز جدید
# ─────────────────────────────────────────────────────────────────
def password_reset_otp(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    phone = request.session.get('otp_phone', '')
    if not phone:
        messages.error(request, 'جلسه منقضی شده است. دوباره تلاش کنید.')
        return redirect('accounts:password_reset_request')

    if request.method == 'POST':
        code = request.POST.get('otp_code', '').strip()
        p1   = request.POST.get('password1', '')
        p2   = request.POST.get('password2', '')

        # پیدا کردن کاربر بر اساس شماره موبایل
        from accounts.models import UserProfile as UP
        profile_qs = UP.objects.filter(phone=phone).select_related('user')
        if not profile_qs.exists():
            messages.error(request, 'خطا در بازیابی اطلاعات. دوباره تلاش کنید.')
            return redirect('accounts:password_reset_request')

        user = profile_qs.first().user
        from core.sms import can_verify_otp, mark_otp_verify_failed, clear_otp_verify_attempts
        ok, err = can_verify_otp(phone, scope='reset')
        if not ok:
            messages.error(request, err)
            return redirect('accounts:password_reset_request')

        otp = OTPCode.objects.filter(user=user, code=code, is_used=False).order_by('-created_at').first()

        if not otp or not otp.is_valid():
            mark_otp_verify_failed(phone, scope='reset')
            messages.error(request, 'کد تأیید نامعتبر یا منقضی شده است.')
            return render(request, 'accounts/password_reset_otp.html',
                          {'page_title': 'تأیید کد پیامکی', 'masked_phone': f'{phone[:4]}****{phone[-3:]}'})

        if not p1 or not p2:
            messages.error(request, 'لطفاً هر دو فیلد رمز عبور را پر کنید.')
        elif p1 != p2:
            messages.error(request, 'رمز عبور و تکرار آن یکسان نیستند.')
        elif len(p1) < 8:
            messages.error(request, 'رمز عبور باید حداقل ۸ کاراکتر باشد.')
        else:
            otp.is_used = True
            otp.save()
            clear_otp_verify_attempts(phone, scope='reset')
            user.set_password(p1)
            user.save()
            del request.session['otp_phone']
            messages.success(request, 'رمز عبور با موفقیت تغییر کرد. اکنون وارد شوید.')
            return redirect('accounts:login')

    masked = f'{phone[:4]}****{phone[-3:]}'
    return render(request, 'accounts/password_reset_otp.html',
                  {'page_title': 'تأیید کد پیامکی', 'masked_phone': masked})


# ─────────────────────────────────────────────────────────────────
# مرحله ۲: تأیید توکن و نمایش فرم رمز جدید
# ─────────────────────────────────────────────────────────────────
def password_reset_confirm(request, uidb64, token):
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    valid = user is not None and default_token_generator.check_token(user, token)

    if not valid:
        messages.error(request, 'لینک بازیابی نامعتبر یا منقضی شده است.')
        return redirect('accounts:password_reset_request')

    if request.method == 'POST':
        p1 = request.POST.get('password1', '')
        p2 = request.POST.get('password2', '')
        if not p1 or not p2:
            messages.error(request, 'لطفاً هر دو فیلد رمز عبور را پر کنید.')
        elif p1 != p2:
            messages.error(request, 'رمز عبور و تکرار آن یکسان نیستند.')
        elif len(p1) < 8:
            messages.error(request, 'رمز عبور باید حداقل ۸ کاراکتر باشد.')
        else:
            user.set_password(p1)
            user.save()
            messages.success(request, 'رمز عبور با موفقیت تغییر کرد. اکنون وارد شوید.')
            return redirect('accounts:login')

    return render(request, 'accounts/password_reset_confirm.html', {
        'uidb64': uidb64,
        'token':  token,
        'page_title': 'تنظیم رمز عبور جدید',
    })


def magic_login_request(request):
    """ارسال لینک ورود یک‌بارمصرف به موبایل متقاضی پذیرفته‌شده."""
    from django.urls import reverse
    from admissions.models import Application
    from core.sms import check_rate_limit, normalize_phone, send_sms
    from core.notify import _site_label
    from .magic_login import make_magic_token

    if request.method != 'POST':
        return redirect('admissions:track')

    nid = (request.POST.get('national_id') or '').strip()
    trans = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
    nid = nid.translate(trans)
    nid = ''.join(ch for ch in nid if ch.isdigit())

    # کلید روی کد ملی است نه IP: چند دانشجو پشت یک IP اپراتور
    # نباید همدیگر را قفل کنند.
    allowed, rl_msg = check_rate_limit(
        request, scope='magic_login', limit=5, window=300, identity=nid)
    if not allowed:
        messages.error(request, rl_msg)
        return redirect(f"{reverse('admissions:track')}?q={nid}")

    app = (
        Application.objects.filter(national_id=nid, status='accepted')
        .order_by('-id')
        .first()
    )
    if not app:
        messages.error(request, 'فقط برای درخواست‌های پذیرفته‌شده لینک ورود ارسال می‌شود.')
        return redirect('admissions:track')

    phone = normalize_phone(app.phone)
    if not phone:
        messages.error(request, 'شماره موبایل روی درخواست ثبت نشده است.')
        return redirect(f"{reverse('admissions:track')}?q={nid}")

    user = User.objects.filter(username=nid).first()
    if user is None:
        profile = UserProfile.objects.filter(national_id=nid).select_related('user').first()
        user = profile.user if profile else None

    label = _site_label()
    if user is None:
        reg_url = request.build_absolute_uri(
            reverse('accounts:register') + f'?nid={nid}&from=track'
        )
        send_sms(
            phone,
            f'{label}: حساب ندارید. برای ادامه ثبت‌نام کنید: {reg_url}',
        )
        messages.success(request, 'لینک ساخت حساب به موبایل شما ارسال شد.')
        return redirect(f"{reverse('admissions:track')}?q={nid}")

    token = make_magic_token(user)
    magic_url = request.build_absolute_uri(reverse('accounts:magic_login', args=[token]))
    send_sms(
        phone,
        f'{label}: لینک ورود یک‌بارمصرف (۳۰ دقیقه): {magic_url}',
    )
    messages.success(request, 'لینک ورود یک‌بارمصرف به موبایل شما ارسال شد.')
    return redirect(f"{reverse('admissions:track')}?q={nid}")


def magic_login(request, token):
    """ورود با لینک یک‌بارمصرف."""
    from .magic_login import consume_magic_token

    user = consume_magic_token(token)
    if not user:
        messages.error(request, 'لینک ورود نامعتبر یا منقضی است. دوباره درخواست دهید.')
        return redirect('accounts:login')

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, f'خوش آمدید، {user.get_full_name() or user.username}!')
    from dashboard.onboarding import next_journey_url
    return redirect(next_journey_url(user=user))
