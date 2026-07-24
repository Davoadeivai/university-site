from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from academics.models import Major
from .models import (
    AdmissionInfo, Application, AdmissionOTP,
    TuitionStructure, TuitionDiscount,
)
import logging
import jdatetime

logger = logging.getLogger('django')

_PERSIAN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
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
    return (value or '').translate(_PERSIAN_DIGITS).strip()


def _parse_jalali_birth(year, month, day):
    """Parse Jalali Y/M/D into a Gregorian date, or None if invalid."""
    try:
        y, m, d = int(year), int(month), int(day)
        return jdatetime.date(y, m, d).togregorian()
    except (TypeError, ValueError, OverflowError):
        return None


def _jalali_birth_context():
    today = jdatetime.date.today()
    years = list(range(today.year - 15, today.year - 70, -1))
    return {
        'jalali_years': years,
        'jalali_months': _JALALI_MONTHS,
        'jalali_days': list(range(1, 32)),
    }


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
            **jalali_ctx,
        }
        if extra:
            ctx.update(extra)
        return render(request, 'admissions/apply.html', ctx)

    if request.method == 'POST':
        p = request.POST
        national_id = _normalize_digits(p.get('national_id', ''))

        # بررسی ثبت تکراری
        if Application.objects.filter(national_id=national_id).exists():
            messages.error(request, 'قبلاً با این کد ملی درخواستی ثبت شده است.')
            return _apply_form(p)

        # اعتبارسنجی اولیه
        errors = []
        if not p.get('first_name'): errors.append('نام الزامی است.')
        if not p.get('last_name'):  errors.append('نام خانوادگی الزامی است.')
        if not national_id or len(national_id) != 10 or not national_id.isdigit():
            errors.append('کد ملی باید ۱۰ رقم باشد.')
        if not p.get('address', '').strip(): errors.append('آدرس الزامی است.')
        if not p.get('degree'):     errors.append('مقطع را انتخاب کنید.')
        if 'doc_national_id' not in request.FILES:
            errors.append('تصویر کارت ملی الزامی است.')

        # موبایل: از session (اگر OTP فعال) یا از فرم
        form_phone = _normalize_digits(p.get('phone', ''))
        if require_otp:
            submit_phone = phone
            phone_verified = True
        else:
            submit_phone = form_phone
            phone_verified = False
            if submit_phone and (
                not submit_phone.isdigit()
                or len(submit_phone) != 11
                or not submit_phone.startswith('09')
            ):
                errors.append('شماره موبایل معتبر وارد کنید (مثال: 09123456789).')

        major_id = p.get('desired_major')
        major2_id = p.get('desired_major2') or None
        major_obj = None
        major2_obj = None
        if not major_id:
            errors.append('رشته اولویت اول را انتخاب کنید.')
        else:
            try:
                major_obj = Major.objects.get(pk=int(major_id), is_active=True)
                if major_obj.admission_degree != p.get('degree'):
                    errors.append('رشته اولویت اول با مقطع انتخاب‌شده هم‌خوان نیست.')
            except (Major.DoesNotExist, ValueError, TypeError):
                errors.append('رشته اولویت اول معتبر نیست.')
        if major2_id:
            try:
                major2_obj = Major.objects.get(pk=int(major2_id), is_active=True)
                if major2_obj.admission_degree != p.get('degree'):
                    errors.append('رشته اولویت دوم با مقطع انتخاب‌شده هم‌خوان نیست.')
                if major_obj and major2_obj.pk == major_obj.pk:
                    errors.append('اولویت اول و دوم نباید یکسان باشند.')
            except (Major.DoesNotExist, ValueError, TypeError):
                errors.append('رشته اولویت دوم معتبر نیست.')
        if not p.get('agreed_terms'): errors.append('پذیرش قوانین الزامی است.')

        # مدرک قبلی باید با مقطع درخواستی سازگار باشد (همه مقاطع یک فرم)
        prev_degree = p.get('prev_degree', 'diploma')
        target_degree = p.get('degree', '')
        allowed_prev = {
            'associate': {'diploma', 'associate'},
            'bachelor':  {'diploma', 'associate', 'bachelor', 'discontinuous_bachelor'},
            'master':    {'bachelor', 'discontinuous_bachelor', 'master'},
            'phd':       {'master'},
        }
        if target_degree in allowed_prev and prev_degree not in allowed_prev[target_degree]:
            labels = {
                'associate': 'کاردانی', 'bachelor': 'کارشناسی',
                'master': 'کارشناسی ارشد', 'phd': 'دکتری',
                'diploma': 'دیپلم', 'discontinuous_bachelor': 'کارشناسی ناپیوسته',
            }
            need = {
                'associate': 'دیپلم یا کاردانی',
                'bachelor': 'دیپلم، کاردانی، کارشناسی یا کارشناسی ناپیوسته',
                'master': 'کارشناسی، کارشناسی ناپیوسته یا کارشناسی ارشد',
                'phd': 'کارشناسی ارشد',
            }
            errors.append(
                f'برای مقطع {labels.get(target_degree, target_degree)} '
                f'آخرین مدرک باید {need[target_degree]} باشد.'
            )

        gpa_val = None
        if p.get('gpa'):
            try:
                gpa_val = float(p.get('gpa'))
            except (TypeError, ValueError):
                errors.append('معدل باید عدد معتبر باشد.')

        birth_date = _parse_jalali_birth(
            _normalize_digits(p.get('birth_year', '')),
            _normalize_digits(p.get('birth_month', '')),
            _normalize_digits(p.get('birth_day', '')),
        )
        if not birth_date:
            errors.append('تاریخ تولد شمسی معتبر وارد کنید.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return _apply_form(p)

        # ذخیره
        app = Application(
            first_name=p.get('first_name', ''),
            last_name=p.get('last_name', ''),
            father_name=p.get('father_name', ''),
            national_id=national_id,
            birth_date=birth_date,
            gender=p.get('gender', 'male'),
            military=p.get('military', 'na'),
            phone=submit_phone,
            phone_emergency=p.get('phone_emergency', ''),
            email=p.get('email', ''),
            address=p.get('address', ''),
            postal_code=p.get('postal_code', ''),
            prev_degree=prev_degree,
            prev_major=p.get('prev_major', ''),
            prev_school=p.get('prev_school', ''),
            prev_grad_year=p.get('prev_grad_year', ''),
            gpa=gpa_val,
            degree=p.get('degree', 'bachelor'),
            desired_major=major_obj,
            desired_major2=major2_obj,
            shift=p.get('shift', 'day'),
            know_from=p.get('know_from', 'site'),
            special_needs=p.get('special_needs', ''),
            agreed_terms=bool(p.get('agreed_terms')),
            phone_verified=phone_verified,
        )

        # آپلود مدارک
        for field in ['doc_national_id', 'doc_prev_degree', 'doc_photo', 'doc_military']:
            if field in request.FILES:
                setattr(app, field, request.FILES[field])

        app.save()

        # پاک کردن session
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
def track_application(request):
    app = None
    query = ''
    timeline = []
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        from core.sms import check_rate_limit
        allowed, rl_msg = check_rate_limit(request, scope='track_app', limit=10, window=300)
        if not allowed:
            messages.error(request, rl_msg)
            query = ''
        else:
            app = Application.objects.filter(
                tracking_code=query
            ).select_related('desired_major', 'desired_major2').first() or Application.objects.filter(
                national_id=query
            ).select_related('desired_major', 'desired_major2').first()
        if query and not app:
            messages.error(request, 'درخواستی با این اطلاعات یافت نشد.')
        else:
            flow = ['pending', 'reviewing', 'incomplete', 'interview', 'accepted']
            labels = dict(Application.STATUS_CHOICES)
            if app.status in ('rejected', 'waiting'):
                timeline = [{
                    'key': app.status,
                    'label': labels.get(app.status, app.status),
                    'state': 'current',
                }]
            else:
                try:
                    cur = flow.index(app.status)
                except ValueError:
                    cur = 0
                for i, key in enumerate(flow):
                    if i < cur:
                        state = 'done'
                    elif i == cur:
                        state = 'current'
                    else:
                        state = 'todo'
                    timeline.append({
                        'key': key,
                        'label': labels[key],
                        'state': state,
                    })
    return render(request, 'admissions/track.html', {
        'app': app,
        'query': query,
        'timeline': timeline,
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
            theory = int(request.POST.get('theory_units', 0) or 0)
            practical = int(request.POST.get('practical_units', 0) or 0)
            lab = int(request.POST.get('lab_units', 0) or 0)
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
                best_discount = discounts.order_by('-percent').first()
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
