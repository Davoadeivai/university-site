from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings as django_settings
from .models import UserProfile, OTPCode


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        national_id = request.POST.get('national_id', '').strip()
        password = request.POST.get('password')
        role = request.POST.get('role', '')

        user = authenticate(request, username=national_id, password=password)
        if user:
            # بررسی تطابق نقش انتخاب‌شده با نقش واقعی کاربر
            try:
                user_role = user.profile.role
            except Exception:
                user_role = ''

            role_labels = {
                'student': 'دانشجو',
                'professor': 'استاد',
                'staff': 'مدیر دانشگاه',
                'admin': 'ادمین',
            }
            if role and user_role and role != user_role:
                messages.error(
                    request,
                    f'شما با نقش «{role_labels.get(user_role, user_role)}» ثبت‌نام کرده‌اید. لطفاً نقش صحیح را انتخاب کنید.'
                )
            else:
                login(request, user)
                messages.success(request, f'خوش آمدید، {user.get_full_name() or user.username}!')
                if user_role == 'admin' or user.is_staff:
                    return redirect('/admin/')
                return redirect(request.GET.get('next', '/dashboard/'))
        else:
            messages.error(request, 'کد ملی یا رمز عبور اشتباه است.')

    context = {'page_title': 'ورود به سامانه'}
    return render(request, 'accounts/login.html', context)


def logout_view(request):
    logout(request)
    messages.info(request, 'با موفقیت خارج شدید.')
    return redirect('/')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        national_id = request.POST.get('national_id', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        role = request.POST.get('role', 'student')
        student_id = request.POST.get('student_id', '').strip()
        department = request.POST.get('department', '').strip()
        phone = request.POST.get('phone', '').strip()

        VALID_ROLES = ['student', 'professor', 'staff']

        if not national_id or not password1 or not password2:
            messages.error(request, 'لطفاً تمام فیلدهای الزامی را پر کنید.')
        elif not national_id.isdigit() or len(national_id) != 10:
            messages.error(request, 'کد ملی باید ۱۰ رقم عددی باشد.')
        elif not phone or not phone.isdigit() or len(phone) != 11 or not phone.startswith('09'):
            messages.error(request, 'شماره موبایل باید ۱۱ رقم و با ۰۹ شروع شود.')
        elif UserProfile.objects.filter(phone=phone).exists():
            messages.error(request, 'این شماره موبایل قبلاً ثبت‌نام شده است.')
        elif role not in VALID_ROLES:
            messages.error(request, 'لطفاً نقش خود را انتخاب کنید.')
        elif password1 != password2:
            messages.error(request, 'رمز عبور و تکرار آن یکسان نیستند.')
        elif len(password1) < 8:
            messages.error(request, 'رمز عبور باید حداقل ۸ کاراکتر باشد.')
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
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.national_id = national_id
            profile.student_id = student_id
            profile.department = department
            profile.phone = phone
            profile.save()
            login(request, user)
            messages.success(request, f'حساب کاربری با موفقیت ساخته شد. خوش آمدید، {user.get_full_name() or national_id}!')
            return redirect('dashboard:dashboard')

    context = {'page_title': 'ثبت‌نام'}
    return render(request, 'accounts/register.html', context)


@login_required
def profile(request):
    profile_obj, created = UserProfile.objects.get_or_create(user=request.user)
    context = {
        'profile': profile_obj,
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
                subject = 'بازیابی رمز عبور — دانشگاه جامع'
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
                    pass
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

                from core.sms import can_send_otp, mark_otp_sent, send_sms
                ok, err = can_send_otp(phone, scope='reset')
                if not ok:
                    messages.error(request, err)
                    return render(request, 'accounts/password_reset_request.html',
                                  {'page_title': 'بازیابی رمز عبور', 'active_method': 'sms'})

                send_sms(phone, sms_text)
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
