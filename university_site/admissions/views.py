from __future__ import annotations

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from academics.models import Major
from core.iran import (
    choice_value,
    is_valid_email,
    is_valid_mobile,
    is_valid_national_id,
    normalize_digits,
    only_digits,
    parse_gpa,
    validate_image_upload,
)
from .models import (
    AdmissionInfo, Application, AdmissionOTP,
    TuitionStructure, TuitionDiscount,
)
import logging
import jdatetime

logger = logging.getLogger('django')

_JALALI_MONTHS = [
    (1, 'فروردین'), (2, 'اردیبهشت'), (3, 'خرداد'),
    (4, 'تیر'), (5, 'مرداد'), (6, 'شهریور'),
    (7, 'مهر'), (8, 'آبان'), (9, 'آذر'),
    (10, 'دی'), (11, 'بهمن'), (12, 'اسفند'),
]


def _require_mobile_otp():
    return bool(getattr(settings, 'ADMISSION_REQUIRE_MOBILE_OTP', False))


def _normalize_digits(value):
    """Convert Persian/Arabic digits to ASCII."""
    return normalize_digits(value)


def _parse_jalali_birth(year, month, day):
    """Parse Jalali Y/M/D into a Gregorian date, or None if invalid."""
    try:
        y, m, d = int(year), int(month), int(day)
        return jdatetime.date(y, m, d).togregorian()
    except (TypeError, ValueError, OverflowError):
        return None


def _jalali_birth_context():
    today = jdatetime.date.today()
    # از ۱۵ تا ۷۵ سالگی (سال انتهایی inclusive)
    years = list(range(today.year - 15, today.year - 76, -1))
    return {
        'jalali_years': years,
        'jalali_months': _JALALI_MONTHS,
        'jalali_days': list(range(1, 32)),
    }


def _active_application_exists(national_id: str = '', phone: str = '') -> Application | None:
    """درخواست فعال (غیر از رد شده) برای کد ملی / موبایل."""
    qs = Application.objects.exclude(status='rejected')
    if national_id:
        hit = qs.filter(national_id=national_id).order_by('-id').first()
        if hit:
            return hit
    if phone:
        return qs.filter(phone=phone).order_by('-id').first()
    return None


def admissions_view(request):
    admission_infos = AdmissionInfo.objects.filter(is_active=True)
    context = {
        'admission_infos': admission_infos,
        'page_title': 'پذیرش دانشجو',
    }
    return render(request, 'admissions/admissions.html', context)


# ─────────────────────────────────────────────
#  مرحله ۱: ارسال OTP
# ─────────────────────────────────────────────
def apply_otp_send(request):
    """ارسال کد OTP برای تأیید موبایل"""
    if not _require_mobile_otp():
        return redirect('admissions:apply')

    from core.sms import can_send_otp, mark_otp_sent, send_otp

    if request.method == 'POST':
        phone = _normalize_digits(request.POST.get('phone', ''))
        if not phone or not phone.isdigit() or len(phone) != 11 or not phone.startswith('09'):
            messages.error(request, 'شماره موبایل معتبر وارد کنید (مثال: 09123456789)')
            return render(request, 'admissions/apply_step1_otp.html',
                          {'page_title': 'ثبت درخواست پذیرش'})

        ok, err = can_send_otp(phone, scope='admission')
        if not ok:
            messages.error(request, err)
            return render(request, 'admissions/apply_step1_otp.html',
                          {'page_title': 'ثبت درخواست پذیرش'})

        otp = AdmissionOTP.create_for_phone(phone)
        msg = f'کد تأیید پذیرش دانشگاه: {otp.code}\nاعتبار ۱۰ دقیقه'
        sent = send_otp(phone, otp.code, msg)
        if not sent:
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            messages.error(request, 'ارسال پیامک ناموفق بود. لطفاً چند لحظه دیگر تلاش کنید.')
            return render(request, 'admissions/apply_step1_otp.html',
                          {'page_title': 'ثبت درخواست پذیرش'})

        mark_otp_sent(phone, scope='admission')
        request.session['apply_phone'] = phone
        messages.success(request, f'کد تأیید به {phone[:4]}****{phone[-3:]} ارسال شد.')
        return redirect('admissions:apply_otp_verify')

    return render(request, 'admissions/apply_step1_otp.html',
                  {'page_title': 'ثبت درخواست پذیرش'})


def apply_otp_verify(request):
    """تأیید کد OTP"""
    if not _require_mobile_otp():
        return redirect('admissions:apply')

    from core.sms import can_verify_otp, mark_otp_verify_failed, clear_otp_verify_attempts

    phone = request.session.get('apply_phone', '')
    if not phone:
        return redirect('admissions:apply_otp_send')

    if request.method == 'POST':
        ok, err = can_verify_otp(phone, scope='admission')
        if not ok:
            messages.error(request, err)
            return redirect('admissions:apply_otp_send')

        code = _normalize_digits(request.POST.get('otp_code', ''))
        otp = AdmissionOTP.objects.filter(
            phone=phone, is_used=False
        ).order_by('-created_at').first()

        if not otp or not otp.is_valid() or otp.code != code:
            if otp:
                otp.attempts += 1
                otp.save(update_fields=['attempts'])
            mark_otp_verify_failed(phone, scope='admission')
            messages.error(request, 'کد تأیید نادرست یا منقضی است.')
        else:
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            clear_otp_verify_attempts(phone, scope='admission')
            request.session['apply_phone_verified'] = True
            return redirect('admissions:apply')

    masked = f'{phone[:4]}****{phone[-3:]}'
    return render(request, 'admissions/apply_step2_verify.html',
                  {'page_title': 'تأیید موبایل', 'masked_phone': masked})


# ─────────────────────────────────────────────
#  مرحله ۳: فرم اصلی پذیرش
# ─────────────────────────────────────────────
def apply(request):
    require_otp = _require_mobile_otp()
    phone = request.session.get('apply_phone', '')
    verified = request.session.get('apply_phone_verified', False)
    preselect_degree = (request.GET.get('degree') or '').strip()

    if require_otp and (not phone or not verified):
        messages.warning(request, 'لطفاً ابتدا شماره موبایل خود را تأیید کنید.')
        return redirect('admissions:apply_otp_send')

    all_majors = Major.objects.filter(is_active=True).order_by('degree', 'name')
    jalali_ctx = _jalali_birth_context()

    def _apply_form(post=None, extra=None):
        ctx = {
            'page_title': 'فرم ثبت درخواست پذیرش',
            'phone': phone,
            'require_mobile_otp': require_otp,
            'all_majors': all_majors,
            'post': post,
            'preselect_degree': preselect_degree,
            'prev_degree_choices': Application.PREV_DEGREE_CHOICES,
            'tips': [
                'مدارک را واضح و رنگی آپلود کنید (حداکثر ۲ مگابایت).',
                'کد رهگیری را بعد از ثبت حتماً ذخیره کنید.',
                'تاریخ تولد را به‌صورت شمسی انتخاب کنید.',
            ],
            **jalali_ctx,
        }
        if extra:
            ctx.update(extra)
        return render(request, 'admissions/apply.html', ctx)

    if request.method == 'POST':
        p = request.POST
        national_id = only_digits(p.get('national_id', ''))
        errors = []

        if not (p.get('first_name') or '').strip():
            errors.append('نام الزامی است.')
        if not (p.get('last_name') or '').strip():
            errors.append('نام خانوادگی الزامی است.')
        if not is_valid_national_id(national_id):
            errors.append('کد ملی معتبر نیست.')
        if not (p.get('address') or '').strip():
            errors.append('آدرس الزامی است.')

        degree = choice_value(p.get('degree', ''), Application.DEGREE_CHOICES)
        if not degree:
            errors.append('مقطع را انتخاب کنید.')
        else:
            info = AdmissionInfo.objects.filter(degree=degree, is_active=True).first()
            if info and not info.is_open:
                errors.append(f'پذیرش مقطع {info.get_degree_display()} در حال حاضر بسته است.')
            if info and info.capacity and info.capacity > 0:
                accepted = Application.objects.filter(degree=degree, status='accepted').count()
                if accepted >= info.capacity:
                    errors.append('ظرفیت این مقطع تکمیل شده است.')

        if 'doc_national_id' not in request.FILES:
            errors.append('تصویر کارت ملی الزامی است.')

        form_phone = only_digits(p.get('phone', ''))
        if require_otp:
            submit_phone = phone
            phone_verified = True
        else:
            submit_phone = form_phone
            phone_verified = False
            if submit_phone and not is_valid_mobile(submit_phone):
                errors.append('شماره موبایل معتبر وارد کنید (مثال: ۰۹۱۲۳۴۵۶۷۸۹).')

        dup = _active_application_exists(national_id=national_id, phone=submit_phone or '')
        if dup:
            errors.append(
                f'قبلاً درخواست فعالی با کد رهگیری {dup.tracking_code} ثبت شده است. '
                'در صورت رد شدن می‌توانید دوباره ثبت کنید.'
            )

        gender = choice_value(p.get('gender', 'male'), Application.GENDER_CHOICES, 'male')
        military = choice_value(p.get('military', 'na'), Application.MILITARY_CHOICES, 'na')
        if gender == 'female':
            military = 'na'
        shift = choice_value(p.get('shift', 'day'), Application.SHIFT_CHOICES, 'day')
        know_from = choice_value(p.get('know_from', 'site'), Application.KNOW_FROM_CHOICES, 'site')
        prev_degree = choice_value(
            p.get('prev_degree', 'diploma'), Application.PREV_DEGREE_CHOICES, 'diploma'
        )

        email = (p.get('email') or '').strip()
        if not is_valid_email(email):
            errors.append('ایمیل معتبر نیست.')

        postal_code = only_digits(p.get('postal_code', ''))
        if postal_code and len(postal_code) not in (0, 10):
            errors.append('کد پستی باید ۱۰ رقم باشد.')
        phone_emergency = only_digits(p.get('phone_emergency', ''))
        prev_grad_year = only_digits(p.get('prev_grad_year', ''))

        major_id = p.get('desired_major')
        major2_id = p.get('desired_major2') or None
        major_obj = major2_obj = None
        if not major_id:
            errors.append('رشته اولویت اول را انتخاب کنید.')
        else:
            try:
                major_obj = Major.objects.get(pk=int(major_id), is_active=True)
                if degree and major_obj.admission_degree != degree:
                    errors.append('رشته اولویت اول با مقطع انتخاب‌شده هم‌خوان نیست.')
                if getattr(major_obj, 'capacity', 0):
                    enrolled = Application.objects.filter(
                        desired_major=major_obj, status='accepted'
                    ).count()
                    if enrolled >= major_obj.capacity:
                        errors.append('ظرفیت رشته اولویت اول تکمیل شده است.')
            except (Major.DoesNotExist, ValueError, TypeError):
                errors.append('رشته اولویت اول معتبر نیست.')
        if major2_id:
            try:
                major2_obj = Major.objects.get(pk=int(major2_id), is_active=True)
                if degree and major2_obj.admission_degree != degree:
                    errors.append('رشته اولویت دوم با مقطع انتخاب‌شده هم‌خوان نیست.')
                if major_obj and major2_obj.pk == major_obj.pk:
                    errors.append('اولویت اول و دوم نباید یکسان باشند.')
            except (Major.DoesNotExist, ValueError, TypeError):
                errors.append('رشته اولویت دوم معتبر نیست.')

        if not p.get('agreed_terms'):
            errors.append('پذیرش قوانین الزامی است.')

        allowed_prev = {
            'associate': {'diploma', 'associate'},
            'bachelor': {'diploma', 'associate', 'bachelor', 'discontinuous_bachelor'},
            'master': {'bachelor', 'discontinuous_bachelor', 'master'},
            'phd': {'master'},
        }
        if degree in allowed_prev and prev_degree not in allowed_prev[degree]:
            need = {
                'associate': 'دیپلم یا کاردانی',
                'bachelor': 'دیپلم، کاردانی، کارشناسی یا کارشناسی ناپیوسته',
                'master': 'کارشناسی، کارشناسی ناپیوسته یا کارشناسی ارشد',
                'phd': 'کارشناسی ارشد',
            }
            errors.append(
                f'برای این مقطع، آخرین مدرک باید {need[degree]} باشد.'
            )

        gpa_val, gpa_err = parse_gpa(p.get('gpa'))
        if gpa_err:
            errors.append(gpa_err)

        birth_year = _normalize_digits(p.get('birth_year', ''))
        birth_month = _normalize_digits(p.get('birth_month', ''))
        birth_day = _normalize_digits(p.get('birth_day', ''))
        if not birth_year or not birth_month or not birth_day:
            errors.append('تاریخ تولد شمسی الزامی است.')
            birth_date = None
        else:
            birth_date = _parse_jalali_birth(birth_year, birth_month, birth_day)
            if not birth_date:
                errors.append('تاریخ تولد شمسی معتبر نیست.')

        for field_name, label in [
            ('doc_national_id', 'کارت ملی'),
            ('doc_prev_degree', 'مدرک تحصیلی'),
            ('doc_photo', 'عکس پرسنلی'),
            ('doc_military', 'مدرک نظام وظیفه'),
        ]:
            err = validate_image_upload(request.FILES.get(field_name), label)
            if err:
                errors.append(err)

        if errors:
            for e in errors:
                messages.error(request, e)
            return _apply_form(p)

        app = Application(
            first_name=(p.get('first_name') or '').strip(),
            last_name=(p.get('last_name') or '').strip(),
            father_name=(p.get('father_name') or '').strip(),
            national_id=national_id,
            birth_date=birth_date,
            gender=gender or 'male',
            military=military or 'na',
            phone=submit_phone or '',
            phone_emergency=phone_emergency,
            email=email,
            address=(p.get('address') or '').strip(),
            postal_code=postal_code,
            prev_degree=prev_degree or 'diploma',
            prev_major=(p.get('prev_major') or '').strip(),
            prev_school=(p.get('prev_school') or '').strip(),
            prev_grad_year=prev_grad_year,
            gpa=gpa_val,
            degree=degree or 'bachelor',
            desired_major=major_obj,
            desired_major2=major2_obj,
            shift=shift or 'day',
            know_from=know_from or 'site',
            special_needs=(p.get('special_needs') or '').strip(),
            agreed_terms=True,
            phone_verified=phone_verified,
        )
        for field in ['doc_national_id', 'doc_prev_degree', 'doc_photo', 'doc_military']:
            if field in request.FILES:
                setattr(app, field, request.FILES[field])

        try:
            app.save()
        except Exception:
            logger.exception('application save failed')
            messages.error(request, 'ثبت درخواست با خطا مواجه شد. دوباره تلاش کنید.')
            return _apply_form(p)

        request.session.pop('apply_phone', None)
        request.session.pop('apply_phone_verified', None)
        messages.success(request, f'درخواست شما با کد رهگیری {app.tracking_code} ثبت شد.')
        return redirect('admissions:apply_success', code=app.tracking_code)

    return _apply_form()


def apply_success(request, code):
    app = get_object_or_404(
        Application.objects.select_related('desired_major', 'desired_major2'),
        tracking_code=code,
    )
    return render(request, 'admissions/apply_success.html', {
        'app': app, 'page_title': 'ثبت موفق درخواست'
    })


# ─────────────────────────────────────────────
#  پیگیری وضعیت
# ─────────────────────────────────────────────
def _normalize_track_query(raw):
    """نرمال‌سازی کد رهگیری / کد ملی (ارقام فارسی، فاصله، خط تیره)."""
    q = _normalize_digits(raw or '')
    for ch in (' ', '-', '_', '\u200c', '\u200f', '\u200e', '\xa0'):
        q = q.replace(ch, '')
    return q.strip()


def _track_lookup_candidates(query):
    """نامزدهای جستجو برای کد ملی / رهگیری با اختلاف صفر اول و ارقام اضافه."""
    digits = ''.join(ch for ch in query if ch.isdigit())
    cands = set()
    if query:
        cands.add(query)
    if digits:
        cands.add(digits)
        if len(digits) <= 10:
            cands.add(digits.zfill(10))
        stripped = digits.lstrip('0')
        if stripped:
            cands.add(stripped)
            if len(stripped) <= 10:
                cands.add(stripped.zfill(10))
    return [c for c in cands if c]


def track_application(request):
    from django.db.models import Q
    from core.sms import normalize_phone

    # PRG: بعد از POST به GET برو تا نتیجه در آدرس بماند و رفرش خراب نشود
    if request.method == 'POST':
        q = _normalize_track_query(request.POST.get('query', ''))
        if not q:
            messages.error(request, 'لطفاً کد رهگیری یا کد ملی را وارد کنید.')
            return redirect('admissions:track')
        from django.urls import reverse
        from urllib.parse import urlencode
        return redirect(f"{reverse('admissions:track')}?{urlencode({'q': q})}")

    app = None
    timeline = []
    query = _normalize_track_query(request.GET.get('q', ''))
    if query:
        qs = Application.objects.select_related(
            'desired_major', 'desired_major2',
        )
        candidates = _track_lookup_candidates(query)
        app = qs.filter(
            Q(tracking_code__in=candidates) | Q(national_id__in=candidates)
        ).first()
        if app is None:
            phone = normalize_phone(query)
            if phone and len(phone) >= 10:
                app = qs.filter(phone=phone).first()
        if app is None:
            messages.error(
                request,
                'درخواستی با این کد رهگیری یا کد ملی یافت نشد. '
                'کد رهگیری ۱۲ رقمی یا کد ملی ۱۰ رقمی را دوباره وارد کنید؛ '
                'اگر هنوز ثبت نکرده‌اید از «ثبت درخواست» اقدام کنید.',
            )
        else:
            labels = dict(Application.STATUS_CHOICES)
            # مسیر واقعی بدون علامت‌زدن مراحل ردشده به‌عنوان انجام‌شده
            main_flow = ['pending', 'reviewing', 'accepted']
            optional = {'incomplete', 'interview'}
            if app.status in ('rejected', 'waiting'):
                timeline = [{
                    'key': app.status,
                    'label': labels.get(app.status, app.status),
                    'state': 'current',
                }]
            elif app.status in optional:
                timeline = [
                    {'key': 'pending', 'label': labels['pending'], 'state': 'done'},
                    {'key': 'reviewing', 'label': labels['reviewing'], 'state': 'done'},
                    {'key': app.status, 'label': labels[app.status], 'state': 'current'},
                    {'key': 'accepted', 'label': labels['accepted'], 'state': 'todo'},
                ]
            else:
                try:
                    cur = main_flow.index(app.status)
                except ValueError:
                    cur = 0
                for i, key in enumerate(main_flow):
                    state = 'done' if i < cur else ('current' if i == cur else 'todo')
                    timeline.append({'key': key, 'label': labels[key], 'state': state})
                if app.status == 'accepted' and app.interview_date:
                    timeline.insert(-1, {
                        'key': 'interview',
                        'label': labels['interview'],
                        'state': 'done',
                    })
    journey = None
    viewer_is_staff = False
    if request.user.is_authenticated:
        try:
            role = request.user.profile.role
        except Exception:
            role = ''
        viewer_is_staff = bool(
            request.user.is_superuser
            or request.user.is_staff
            or role in ('admin', 'staff')
        )
    if app and app.status == 'accepted':
        from dashboard.onboarding import build_journey_status
        user = request.user if request.user.is_authenticated else None
        # اگر کاربر لاگین است ولی کد ملی‌اش با درخواست یکی نیست، فقط وضعیت عمومی را نشان بده
        if user and hasattr(user, 'profile'):
            uid = (getattr(user.profile, 'national_id', '') or user.username or '').strip()
            if uid and uid != (app.national_id or '').strip():
                user = None
        journey = build_journey_status(user=user, national_id=app.national_id)

    return render(request, 'admissions/track.html', {
        'app': app,
        'query': query,
        'timeline': timeline,
        'journey': journey,
        'viewer_is_staff': viewer_is_staff,
        'page_title': 'پیگیری وضعیت درخواست',
    })


# ─────────────────────────────────────────────
#  شهریه‌ساز آنلاین
# ─────────────────────────────────────────────
def tuition_calculator(request):
    tuitions = TuitionStructure.objects.filter(
        is_active=True
    ).select_related('major', 'major__group').order_by('major__degree', 'major__name')
    discounts = TuitionDiscount.objects.filter(is_active=True)
    history = TuitionStructure.objects.filter(
        is_active=False
    ).select_related('major').order_by('-academic_year')[:20]

    result = None
    if request.method == 'POST':
        major_id = request.POST.get('major_id', '')
        try:
            theory = max(0, min(40, int(only_digits(request.POST.get('theory_units', 0) or 0) or 0)))
            practical = max(0, min(40, int(only_digits(request.POST.get('practical_units', 0) or 0) or 0)))
            lab = max(0, min(40, int(only_digits(request.POST.get('lab_units', 0) or 0) or 0)))
        except (TypeError, ValueError):
            messages.error(request, 'تعداد واحدها باید عدد معتبر باشد.')
            theory = practical = lab = 0
        else:
            ts = TuitionStructure.objects.filter(
                major_id=major_id, is_active=True
            ).select_related('major').order_by('-academic_year').first()
            if ts:
                theory_cost = ts.theory_fee * theory
                practical_cost = ts.practical_fee * practical
                lab_cost = ts.lab_fee * lab
                extra = ts.registration_fee + ts.insurance_fee + ts.card_fee
                subtotal = ts.fixed_fee + theory_cost + practical_cost + lab_cost + extra
                # تخفیف فقط نمایش راهنما — بدون اعمال خودکار بیشینه
                discount_code = (request.POST.get('discount_id') or '').strip()
                best_discount = None
                if discount_code.isdigit():
                    best_discount = discounts.filter(pk=int(discount_code)).first()
                discount_amount = 0
                if best_discount:
                    discount_amount = subtotal * best_discount.percent / 100
                total = subtotal - discount_amount
                result = {
                    'ts': ts,
                    'theory_cost': theory_cost,
                    'practical_cost': practical_cost,
                    'lab_cost': lab_cost,
                    'extra': extra,
                    'subtotal': subtotal,
                    'discount': best_discount,
                    'discount_amount': discount_amount,
                    'total': total,
                    'theory': theory,
                    'practical': practical,
                    'lab': lab,
                    'note': 'مبالغ تقریبی است؛ فاکتور نهایی پس از پذیرش در پنل دانشجو صادر می‌شود.',
                }
            else:
                messages.warning(request, 'اطلاعات شهریه برای این رشته ثبت نشده است.')

    # گروه‌بندی بر اساس کد مقطع برای فیلتر JS
    degrees = []
    seen = set()
    for t in tuitions:
        code = t.major.degree
        if code not in seen:
            seen.add(code)
            degrees.append({'code': code, 'label': t.major.get_degree_display()})

    return render(request, 'admissions/tuition_calculator.html', {
        'tuitions': tuitions,
        'degrees': degrees,
        'discounts': discounts,
        'history': history,
        'result': result,
        'page_title': 'محاسبه‌گر شهریه',
    })


def complete_documents(request, code):
    """آپلود مجدد مدارک وقتی وضعیت incomplete است."""
    from django.urls import reverse
    from urllib.parse import urlencode

    app = get_object_or_404(Application, tracking_code=code, status='incomplete')
    if request.method == 'POST':
        errors = []
        updated = False
        for field_name, label in [
            ('doc_national_id', 'کارت ملی'),
            ('doc_prev_degree', 'مدرک تحصیلی'),
            ('doc_photo', 'عکس پرسنلی'),
            ('doc_military', 'مدرک نظام وظیفه'),
        ]:
            f = request.FILES.get(field_name)
            if f:
                err = validate_image_upload(f, label)
                if err:
                    errors.append(err)
                else:
                    setattr(app, field_name, f)
                    updated = True
        if errors:
            for e in errors:
                messages.error(request, e)
        elif not updated:
            messages.error(request, 'حداقل یک مدرک جدید آپلود کنید.')
        else:
            app.status = 'reviewing'
            app.save()
            messages.success(request, 'مدارک ارسال شد و دوباره برای بررسی قرار گرفت.')
            return redirect(f"{reverse('admissions:track')}?{urlencode({'q': app.tracking_code})}")
    return render(request, 'admissions/complete_documents.html', {
        'app': app,
        'page_title': 'تکمیل مدارک',
    })


def tuition_info(request):
    tuitions = TuitionStructure.objects.filter(
        is_active=True
    ).select_related('major', 'major__group').order_by('major__degree', 'major__name')
    discounts = TuitionDiscount.objects.filter(is_active=True)
    history = TuitionStructure.objects.filter(
        is_active=False
    ).select_related('major').order_by('-academic_year', 'major__name')
    return render(request, 'admissions/tuition_info.html', {
        'tuitions': tuitions,
        'discounts': discounts,
        'history': history,
        'page_title': 'اطلاعات شهریه',
    })
