from __future__ import annotations

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from academics.models import Major
from core.jalali import format_jalali_date
from core.models import SiteSettings
from core.iran import (
    IRAN_PROVINCES,
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
    AdmissionInfo, Application, AdmissionOTP, ApplicationDraft,
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
    from core.degree_map import CANONICAL_DEGREES

    order = {code: i for i, (code, _) in enumerate(CANONICAL_DEGREES)}
    infos = list(AdmissionInfo.objects.filter(is_active=True))
    infos.sort(key=lambda x: order.get(x.degree, 100))
    context = {
        'admission_infos': infos,
        'page_title': 'پذیرش دانشجو',
    }
    return render(request, 'admissions/admissions.html', context)


# ─────────────────────────────────────────────
#  مرحله ۱: ارسال OTP
# ─────────────────────────────────────────────
def apply_otp_send(request):
    """ارسال کد OTP برای تأیید موبایل"""
    from django.urls import reverse
    from urllib.parse import urlencode

    # deeplink از مسیر دانشجو
    from core.degree_map import to_canonical_degree
    for key in ('degree', 'major', 'major_id'):
        val = (request.GET.get(key) or '').strip()
        if val:
            if key == 'degree':
                val = to_canonical_degree(val) or val
            request.session[f'apply_pre_{key}'] = val

    def _apply_redirect():
        params = {}
        degree = to_canonical_degree(
            request.session.get('apply_pre_degree') or ''
        ) or (request.session.get('apply_pre_degree') or '')
        major = (
            request.session.get('apply_pre_major')
            or request.session.get('apply_pre_major_id')
            or ''
        )
        if degree:
            params['degree'] = degree
            request.session['apply_pre_degree'] = degree
        if major:
            params['major'] = major
        target = reverse('admissions:apply')
        if params:
            target += '?' + urlencode(params)
        return redirect(target)

    if not _require_mobile_otp():
        return _apply_redirect()

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
    from django.urls import reverse
    from urllib.parse import urlencode
    from core.degree_map import to_canonical_degree

    def _apply_redirect():
        params = {}
        degree = to_canonical_degree(
            request.session.get('apply_pre_degree') or ''
        ) or (request.session.get('apply_pre_degree') or '')
        major = (
            request.session.get('apply_pre_major')
            or request.session.get('apply_pre_major_id')
            or ''
        )
        if degree:
            params['degree'] = degree
            request.session['apply_pre_degree'] = degree
        if major:
            params['major'] = major
        target = reverse('admissions:apply')
        if params:
            target += '?' + urlencode(params)
        return redirect(target)

    if not _require_mobile_otp():
        return _apply_redirect()

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
            return _apply_redirect()

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
    preselect_degree = (request.GET.get('degree') or request.session.get('apply_pre_degree') or '').strip()
    preselect_major = (
        request.GET.get('major')
        or request.GET.get('major_id')
        or request.session.get('apply_pre_major')
        or request.session.get('apply_pre_major_id')
        or ''
    ).strip()
    if preselect_degree:
        from core.degree_map import to_canonical_degree
        preselect_degree = to_canonical_degree(preselect_degree) or preselect_degree

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
            'preselect_major': preselect_major,
            'degree_choices': [
                c for c in Application.DEGREE_CHOICES
                if c[0] in {
                    'associate_cont', 'bachelor_disc', 'bachelor_cont',
                    'associate_tech', 'master',
                }
            ],
            'prev_degree_choices': Application.PREV_DEGREE_CHOICES,
            'quota_choices': Application.QUOTA_CHOICES,
            'diploma_type_choices': Application.DIPLOMA_TYPE_CHOICES,
            'marital_choices': Application.MARITAL_CHOICES,
            'province_choices': IRAN_PROVINCES,
            'tips': [
                'مدارک را واضح و رنگی آپلود کنید (حداکثر ۲ مگابایت).',
                'کد رهگیری را بعد از ثبت حتماً ذخیره کنید.',
                'تاریخ تولد را به‌صورت شمسی انتخاب کنید.',
            ],
            **jalali_ctx,
        }
        # پیش‌نویس فقط وقتی معنا دارد که هنوز چیزی POST نشده؛ بعد از
        # ارسال، مقادیر خودِ فرم مرجع‌اند نه چیزی که قبلاً ذخیره شده.
        if post is None and phone:
            draft = ApplicationDraft.objects.filter(phone=phone).first()
            if draft and draft.payload:
                ctx['draft'] = draft.payload
                ctx['draft_ratio'] = draft.filled_ratio()
                ctx['draft_saved_at'] = draft.updated_at
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
        if degree:
            from core.degree_map import to_canonical_degree
            degree = to_canonical_degree(degree) or degree
        if not degree:
            errors.append('مقطع را انتخاب کنید.')
        else:
            info = AdmissionInfo.objects.filter(degree=degree, is_active=True).first()
            if not info:
                # سازگاری با رکورد قدیمی associate/bachelor
                from core.degree_map import LEGACY_TO_CANONICAL
                legacy = [k for k, v in LEGACY_TO_CANONICAL.items() if v == degree]
                info = AdmissionInfo.objects.filter(degree__in=legacy, is_active=True).first()
            if info and not info.is_open:
                errors.append(f'پذیرش مقطع {info.get_degree_display()} در حال حاضر بسته است.')
            if info and info.capacity and info.capacity > 0:
                accepted = Application.objects.filter(degree=degree, status='accepted').count()
                if accepted >= info.capacity:
                    errors.append('ظرفیت این مقطع تکمیل شده است.')

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
        from core.degree_map import degrees_compatible
        if not major_id:
            errors.append('رشته اولویت اول را انتخاب کنید.')
        else:
            try:
                major_obj = Major.objects.get(pk=int(major_id), is_active=True)
                if degree and not degrees_compatible(degree, major_obj.degree):
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
                if degree and not degrees_compatible(degree, major2_obj.degree):
                    errors.append('رشته اولویت دوم با مقطع انتخاب‌شده هم‌خوان نیست.')
                if major_obj and major2_obj.pk == major_obj.pk:
                    errors.append('اولویت اول و دوم نباید یکسان باشند.')
            except (Major.DoesNotExist, ValueError, TypeError):
                errors.append('رشته اولویت دوم معتبر نیست.')

        if not p.get('agreed_terms'):
            errors.append('پذیرش قوانین الزامی است.')

        allowed_prev = {
            'associate_cont': {'diploma', 'associate'},
            'associate_tech': {'diploma', 'associate'},
            'bachelor_cont': {'diploma', 'associate', 'bachelor', 'discontinuous_bachelor'},
            'bachelor_disc': {'associate', 'diploma', 'discontinuous_bachelor'},
            'master': {'bachelor', 'discontinuous_bachelor', 'master'},
            'associate': {'diploma', 'associate'},
            'bachelor': {'diploma', 'associate', 'bachelor', 'discontinuous_bachelor'},
            'phd': {'master'},
        }
        if degree in allowed_prev and prev_degree not in allowed_prev[degree]:
            need = {
                'associate_cont': 'دیپلم یا کاردانی',
                'associate_tech': 'دیپلم یا کاردانی',
                'bachelor_cont': 'دیپلم، کاردانی، کارشناسی یا کارشناسی ناپیوسته',
                'bachelor_disc': 'کاردانی یا معادل',
                'master': 'کارشناسی، کارشناسی ناپیوسته یا کارشناسی ارشد',
                'associate': 'دیپلم یا کاردانی',
                'bachelor': 'دیپلم، کاردانی، کارشناسی یا کارشناسی ناپیوسته',
                'phd': 'کارشناسی ارشد',
            }
            errors.append(
                f'برای این مقطع، آخرین مدرک باید {need[degree]} باشد.'
            )

        gpa_val, gpa_err = parse_gpa(p.get('gpa'))
        if gpa_err:
            errors.append(gpa_err)

        # ── فیلدهای هویتی و تحصیلی تکمیلی ──
        quota = choice_value(p.get('quota', 'free'), Application.QUOTA_CHOICES, 'free')
        marital_status = choice_value(
            p.get('marital_status', 'single'), Application.MARITAL_CHOICES, 'single'
        )
        diploma_type = choice_value(p.get('diploma_type', ''), Application.DIPLOMA_TYPE_CHOICES, '')
        birth_cert_no = only_digits(p.get('birth_cert_no', ''))
        academic_record_code = only_digits(p.get('academic_record_code', ''))
        province = (p.get('province') or '').strip()
        city = (p.get('city') or '').strip()
        birth_place = (p.get('birth_place') or '').strip()
        issue_place = (p.get('issue_place') or '').strip()
        guardian_name = (p.get('guardian_name') or '').strip()

        if not province:
            errors.append('استان محل سکونت الزامی است.')
        if not city:
            errors.append('شهر محل سکونت الزامی است.')
        if prev_degree == 'diploma' and not diploma_type:
            errors.append('نوع دیپلم را انتخاب کنید.')

        diploma_gpa_val, dgpa_err = parse_gpa(p.get('diploma_gpa'))
        if dgpa_err:
            errors.append(dgpa_err.replace('معدل', 'معدل کتبی دیپلم'))

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

        for field_name, label, required in [
            ('doc_national_id', 'کارت ملی', True),
            ('doc_prev_degree', 'مدرک تحصیلی', False),
            ('doc_military', 'مدرک نظام وظیفه', False),
        ]:
            err = validate_image_upload(request.FILES.get(field_name), label, required=required)
            if err:
                errors.append(err)

        from core.iran import validate_personnel_photo
        hijab_ok = bool(p.get('photo_hijab_confirmed'))
        errors.extend(
            validate_personnel_photo(
                request.FILES.get('doc_photo'),
                gender=gender or '',
                hijab_confirmed=hijab_ok,
                required=True,
            )
        )

        if errors:
            for e in errors:
                messages.error(request, e)
            return _apply_form(p)

        app = Application(
            first_name=(p.get('first_name') or '').strip(),
            last_name=(p.get('last_name') or '').strip(),
            father_name=(p.get('father_name') or '').strip(),
            national_id=national_id,
            birth_cert_no=birth_cert_no,
            birth_place=birth_place,
            issue_place=issue_place,
            birth_date=birth_date,
            gender=gender or 'male',
            marital_status=marital_status or 'single',
            military=military or 'na',
            quota=quota or 'free',
            phone=submit_phone or '',
            phone_emergency=phone_emergency,
            guardian_name=guardian_name,
            email=email,
            province=province,
            city=city,
            address=(p.get('address') or '').strip(),
            postal_code=postal_code,
            prev_degree=prev_degree or 'diploma',
            diploma_type=diploma_type,
            prev_major=(p.get('prev_major') or '').strip(),
            prev_school=(p.get('prev_school') or '').strip(),
            prev_grad_year=prev_grad_year,
            gpa=gpa_val,
            diploma_gpa=diploma_gpa_val,
            academic_record_code=academic_record_code,
            degree=degree or 'bachelor',
            desired_major=major_obj,
            desired_major2=major2_obj,
            shift=shift or 'day',
            know_from=know_from or 'site',
            special_needs=(p.get('special_needs') or '').strip(),
            agreed_terms=True,
            phone_verified=phone_verified,
            photo_hijab_confirmed=hijab_ok if (gender or '') == 'female' else False,
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

        # پرونده ثبت شد؛ پیش‌نویس دیگر کاری ندارد و نباید بماند
        ApplicationDraft.clear(phone)
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
def _mask_phone(phone: str) -> str:
    p = ''.join(ch for ch in (phone or '') if ch.isdigit())
    return f'{p[:4]}****{p[-3:]}' if len(p) >= 8 else '***'


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


def _track_session_key(app_pk) -> str:
    return f'track_ok_{app_pk}'


def _track_is_unlocked(request, app) -> bool:
    """آیا بیننده مجاز به دیدن جزئیات این پرونده است؟

    کد رهگیری ۱۲ رقمی تصادفی است و فقط دست خود متقاضی است، پس خودش
    عامل احراز هویت محسوب می‌شود. اما کد ملی در ایران محرمانه نیست؛
    برای آن تأیید پیامکی به شمارهٔ ثبت‌شده لازم است.
    """
    if request.session.get(_track_session_key(app.pk)):
        return True
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return True
        try:
            role = request.user.profile.role
            uid = (request.user.profile.national_id or request.user.username or '').strip()
        except Exception:
            role, uid = '', (request.user.username or '').strip()
        if role in ('admin', 'staff'):
            return True
        if uid and uid == (app.national_id or '').strip():
            return True
    return False


def track_application(request):
    from django.db.models import Q
    from core.sms import check_rate_limit, normalize_phone

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
    needs_otp = False
    query = _normalize_track_query(request.GET.get('q', ''))
    if query:
        # جلوگیری از پیمایش کد ملی‌ها
        allowed, rl_msg = check_rate_limit(
            request, scope='track', limit=12, window=300, identity=query)
        if not allowed:
            messages.error(request, rl_msg)
            return render(request, 'admissions/track.html', {
                'app': None, 'query': '', 'timeline': [], 'journey': None,
                'viewer_is_staff': False, 'needs_otp': False,
                'page_title': 'پیگیری وضعیت درخواست',
            })

        qs = Application.objects.select_related(
            'desired_major', 'desired_major2',
        )
        candidates = _track_lookup_candidates(query)
        digits = ''.join(ch for ch in query if ch.isdigit())

        # کد رهگیری = راز خود متقاضی → دسترسی مستقیم
        app = qs.filter(tracking_code__in=candidates).first()
        matched_by_code = app is not None

        if app is None:
            app = qs.filter(national_id__in=candidates).first()
            if app is None:
                phone = normalize_phone(query)
                if phone and len(phone) >= 10:
                    app = qs.filter(phone=phone).first()

        if app is not None:
            if matched_by_code:
                request.session[_track_session_key(app.pk)] = True
            elif not _track_is_unlocked(request, app):
                # کد ملی / موبایل محرمانه نیست → تأیید پیامکی لازم است
                needs_otp = True
                request.session['track_pending_pk'] = app.pk
                return render(request, 'admissions/track_verify.html', {
                    'page_title': 'تأیید هویت برای پیگیری',
                    'masked_phone': _mask_phone(app.phone),
                    'query': query,
                })
        if app is None:
            messages.error(
                request,
                'درخواستی با این کد رهگیری یا کد ملی یافت نشد. '
                'کد رهگیری ۱۲ رقمی یا کد ملی ۱۰ رقمی را دوباره وارد کنید؛ '
                'اگر هنوز ثبت نکرده‌اید از «ثبت درخواست» اقدام کنید.',
            )
        else:
            from . import tracking
            timeline = tracking.build(app)
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
        'needs_otp': needs_otp,
        'page_title': 'پیگیری وضعیت درخواست',
    })


def admission_letter(request, code):
    """کارنامهٔ پذیرش قابل چاپ — فقط برای پرونده‌ای که بیننده به آن دسترسی دارد."""
    from django.http import Http404

    from dashboard.barcode import barcode_svg
    from .verification import make_verification_code

    app = (
        Application.objects
        .select_related('desired_major', 'desired_major__department', 'desired_major2')
        .filter(tracking_code=code)
        .first()
    )
    if not app:
        raise Http404('کارنامه‌ای با این کد رهگیری یافت نشد.')
    if app.status != 'accepted':
        messages.info(request, 'کارنامهٔ پذیرش فقط برای پرونده‌های پذیرفته‌شده صادر می‌شود.')
        return redirect('admissions:track')
    if not _track_is_unlocked(request, app):
        request.session['track_pending_pk'] = app.pk
        messages.warning(request, 'برای دریافت کارنامه ابتدا هویت خود را تأیید کنید.')
        return redirect('admissions:track_otp')

    site = SiteSettings.objects.first()
    verification_code = make_verification_code(app)
    verify_path = request.build_absolute_uri(reverse('admissions:verify'))

    return render(request, 'admissions/admission_letter.html', {
        'app': app,
        'site': site,
        'verification_code': verification_code,
        'verify_url': verify_path,
        'barcode': barcode_svg(app.tracking_code, height=48, module_width=2),
        'page_title': f'کارنامه پذیرش — {app.tracking_code}',
    })


def verify_certificate(request):
    """استعلام عمومی اصالت کارنامه — بدون افشای اطلاعات هویتی."""
    from core.sms import check_rate_limit
    from .verification import find_by_code, normalize_code

    raw = (request.GET.get('code') or request.POST.get('code') or '').strip()
    result = None
    checked = False

    if raw:
        allowed, rl_msg = check_rate_limit(
            request, scope='verify', limit=15, window=300, identity=raw)
        if not allowed:
            messages.error(request, rl_msg)
        else:
            checked = True
            app = find_by_code(raw)
            if app:
                result = {
                    'valid': True,
                    'degree': app.get_degree_display(),
                    'major': app.desired_major.name if app.desired_major_id else '—',
                    'year': format_jalali_date(app.created_at, 'short') if app.created_at else '',
                    # فقط حرف اول نام — برای تطبیق کافی است، برای شناسایی نه
                    'initials': f'{(app.first_name or "؟")[:1]}. {(app.last_name or "؟")[:1]}.',
                }
            else:
                result = {'valid': False}

    return render(request, 'admissions/verify.html', {
        'code': normalize_code(raw) if raw else '',
        'result': result,
        'checked': checked,
        'page_title': 'استعلام اصالت کارنامه',
    })


def track_otp(request):
    """ارسال و تأیید کد پیامکی برای باز کردن پیگیری با کد ملی."""
    from django.urls import reverse
    from urllib.parse import urlencode
    from core.sms import (
        can_send_otp, can_verify_otp, clear_otp_verify_attempts,
        mark_otp_sent, mark_otp_verify_failed, send_otp,
    )

    pk = request.session.get('track_pending_pk')
    if not pk:
        return redirect('admissions:track')
    app = Application.objects.filter(pk=pk).first()
    if not app:
        request.session.pop('track_pending_pk', None)
        return redirect('admissions:track')

    query = _normalize_track_query(request.GET.get('q') or request.POST.get('query') or '')
    ctx = {
        'page_title': 'تأیید هویت برای پیگیری',
        'masked_phone': _mask_phone(app.phone),
        'query': query,
    }

    if request.method != 'POST':
        return render(request, 'admissions/track_verify.html', ctx)

    action = request.POST.get('action') or 'send'

    if action == 'send':
        if not app.phone:
            messages.error(request, 'برای این پرونده شماره موبایلی ثبت نشده. با موسسه تماس بگیرید.')
            return render(request, 'admissions/track_verify.html', ctx)
        ok, err = can_send_otp(app.phone, scope='track')
        if not ok:
            messages.error(request, err)
            return render(request, 'admissions/track_verify.html', ctx)
        otp = AdmissionOTP.create_for_phone(app.phone)
        sent = send_otp(app.phone, otp.code, f'کد پیگیری پذیرش: {otp.code}\nاعتبار ۱۰ دقیقه')
        if not sent:
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            messages.error(request, 'ارسال پیامک ناموفق بود. چند لحظه بعد تلاش کنید.')
            return render(request, 'admissions/track_verify.html', ctx)
        mark_otp_sent(app.phone, scope='track')
        messages.success(request, f'کد تأیید به {_mask_phone(app.phone)} ارسال شد.')
        ctx['code_sent'] = True
        return render(request, 'admissions/track_verify.html', ctx)

    # action == 'verify'
    ok, err = can_verify_otp(app.phone, scope='track')
    if not ok:
        messages.error(request, err)
        return redirect('admissions:track')

    code = _normalize_digits(request.POST.get('otp_code', ''))
    otp = (
        AdmissionOTP.objects.filter(phone=app.phone, is_used=False)
        .order_by('-created_at').first()
    )
    if not otp or not otp.is_valid() or otp.code != code:
        if otp:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
        mark_otp_verify_failed(app.phone, scope='track')
        messages.error(request, 'کد تأیید نادرست یا منقضی است.')
        ctx['code_sent'] = True
        return render(request, 'admissions/track_verify.html', ctx)

    otp.is_used = True
    otp.save(update_fields=['is_used'])
    clear_otp_verify_attempts(app.phone, scope='track')
    request.session[_track_session_key(app.pk)] = True
    request.session.pop('track_pending_pk', None)
    target = reverse('admissions:track')
    if query:
        target += '?' + urlencode({'q': query})
    return redirect(target)


# ─────────────────────────────────────────────
#  شهریه‌ساز آنلاین
# ─────────────────────────────────────────────
def tuition_calculator(request):
    from academics.models import Major
    from core.degree_map import CANONICAL_DEGREES, to_canonical_degree

    # اطمینان از وجود ساختار شهریه برای همه رشته‌های فعال (مقاطع بدون داده قبلاً در لیست نبودند)
    from admissions.tuition_seed import ensure_tuition_structures_for_active_majors, needs_tuition_seed
    if needs_tuition_seed():
        ensure_tuition_structures_for_active_majors()

    degree_order = {code: i for i, (code, _) in enumerate(CANONICAL_DEGREES)}
    tuitions = list(
        TuitionStructure.objects.filter(
            is_active=True,
            major__is_active=True,
        ).select_related('major', 'major__group')
    )
    tuitions.sort(
        key=lambda t: (
            degree_order.get(to_canonical_degree(t.major.degree) or t.major.degree, 100),
            t.major.name,
        )
    )
    discounts = TuitionDiscount.objects.filter(is_active=True)
    history = TuitionStructure.objects.filter(
        is_active=False
    ).select_related('major').order_by('-academic_year')[:20]

    preselect_major_id = (
        request.GET.get('major_id') or request.GET.get('major') or ''
    ).strip()
    preselect_degree = to_canonical_degree(request.GET.get('degree') or '')
    if preselect_major_id.isdigit() and not preselect_degree:
        maj = Major.objects.filter(pk=int(preselect_major_id), is_active=True).first()
        if maj:
            preselect_degree = to_canonical_degree(maj.degree) or maj.degree

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
                preselect_degree = to_canonical_degree(ts.major.degree) or ts.major.degree
                preselect_major_id = str(ts.major_id)
            else:
                messages.warning(request, 'اطلاعات شهریه برای این رشته ثبت نشده است.')

    # همیشه هر ۵ مقطع رسمی — نه فقط مقاطعی که قبلاً شهریه داشتند
    degrees = [{'code': code, 'label': label} for code, label in CANONICAL_DEGREES]

    return render(request, 'admissions/tuition_calculator.html', {
        'tuitions': tuitions,
        'degrees': degrees,
        'discounts': discounts,
        'history': history,
        'result': result,
        'preselect_major_id': preselect_major_id,
        'preselect_degree': preselect_degree,
        'page_title': 'محاسبه‌گر شهریه',
    })


def complete_documents(request, code):
    """آپلود مجدد مدارک وقتی وضعیت incomplete است."""
    from django.urls import reverse
    from urllib.parse import urlencode

    app = get_object_or_404(Application, tracking_code=code, status='incomplete')
    if request.method == 'POST':
        from core.iran import validate_personnel_photo
        errors = []
        updated = False
        for field_name, label in [
            ('doc_national_id', 'کارت ملی'),
            ('doc_prev_degree', 'مدرک تحصیلی'),
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

        photo = request.FILES.get('doc_photo')
        hijab_ok = bool(request.POST.get('photo_hijab_confirmed')) or bool(app.photo_hijab_confirmed)
        if photo:
            photo_errors = validate_personnel_photo(
                photo, gender=app.gender, hijab_confirmed=hijab_ok, required=True,
            )
            if not photo_errors:
                app.doc_photo = photo
                updated = True
            errors.extend(photo_errors)
        elif not app.doc_photo:
            errors.append('عکس پرسنلی الزامی است.')
        elif app.gender == 'female' and not hijab_ok:
            errors.append(
                'برای متقاضیان خانم، تأیید رعایت حجاب کامل در عکس پرسنلی الزامی است.'
            )

        if app.gender == 'female' and hijab_ok and not app.photo_hijab_confirmed:
            app.photo_hijab_confirmed = True
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
    from core.degree_map import CANONICAL_DEGREES, to_canonical_degree
    from admissions.tuition_seed import ensure_tuition_structures_for_active_majors, needs_tuition_seed
    if needs_tuition_seed():
        ensure_tuition_structures_for_active_majors()

    degree_order = {code: i for i, (code, _) in enumerate(CANONICAL_DEGREES)}
    tuitions = list(
        TuitionStructure.objects.filter(
            is_active=True,
            major__is_active=True,
        ).select_related('major', 'major__group')
    )
    tuitions.sort(
        key=lambda t: (
            degree_order.get(to_canonical_degree(t.major.degree) or t.major.degree, 100),
            t.major.name,
        )
    )
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


def save_draft(request):
    """ذخیرهٔ خودکار پیش‌نویس فرم پذیرش.

    مرورگر هر چند ثانیه یک بار محتوای فرم را اینجا می‌فرستد. پاسخ
    عمداً کوچک است و هیچ داده‌ای برنمی‌گرداند: این مسیر فقط برای
    نوشتن است.

    کلید، موبایلِ تأییدشده در نشست است. اگر نشستی نباشد ساکت رد
    می‌شود — پیش‌نویس یک راحتی است، نه چیزی که ارزش خطا دادن به
    کاربر وسط پرکردن فرم را داشته باشد.
    """
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    phone = request.session.get('apply_phone', '')
    if not phone:
        return JsonResponse({'ok': False, 'reason': 'no-session'})

    draft = ApplicationDraft.store(phone, request.POST)
    return JsonResponse({'ok': True, 'ratio': draft.filled_ratio()})


def discard_draft(request):
    """دور انداختن پیش‌نویس — وقتی متقاضی می‌خواهد از نو شروع کند."""
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    ApplicationDraft.clear(request.session.get('apply_phone', ''))
    return JsonResponse({'ok': True})
