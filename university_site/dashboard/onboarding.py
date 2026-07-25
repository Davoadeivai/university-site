"""مسیر پس از پذیرش: همگام‌سازی پروفایل، اقساط شهریه، وضعیت مراحل."""
from __future__ import annotations

import hashlib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from admissions.models import Application, TuitionStructure
from accounts.models import UserProfile

from .models import Enrollment, Payment, Semester, StudentDiscountClaim, TuitionInstallmentPlan

# نسبت اقساط پیش‌فرض: اول / میانی / کارت امتحان (جمع = ۱۰۰)
DEFAULT_INSTALLMENT_RATIOS = (40, 30, 30)
DEFAULT_DUE_DAYS = (7, 60, 100)
STAGE_META = (
    (1, 'initial', 'قسط اول — پیش‌پرداخت ثبت‌نام / انتخاب واحد'),
    (2, 'mid', 'قسط دوم — میانی ترم'),
    (3, 'exam_card', 'قسط سوم — تسویه برای کارت ورود به جلسه'),
)


def get_accepted_application(national_id: str) -> Application | None:
    nid = (national_id or '').strip()
    if not nid:
        return None
    qs = (
        Application.objects.filter(national_id=nid, status='accepted')
        .select_related('desired_major', 'desired_major2')
        .order_by('-id')
    )
    # #21: اگر چند Application پذیرفته‌شده با یک کد ملی وجود داشت، هشدار لاگ بده
    count = qs.count()
    if count > 1:
        import logging
        logging.getLogger(__name__).warning(
            'Multiple accepted applications for national_id=%s (count=%d); using latest.',
            nid, count,
        )
    return qs.first()


def sync_profile_from_application(user: User, app: Application | None = None) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    nid = profile.national_id or user.username
    app = app or get_accepted_application(nid)
    if not app:
        return profile

    changed = False
    if not profile.national_id and nid:
        profile.national_id = nid
        changed = True
    # فقط اگر رشته خالی باشد از پذیرش پر کن (بازنویسی دستی ادمین حفظ شود)
    if app.desired_major_id and not profile.major_id:
        profile.major = app.desired_major
        changed = True
    if app.phone and not profile.phone:
        profile.phone = app.phone
        changed = True
    if not user.first_name and app.first_name:
        user.first_name = app.first_name
        user.save(update_fields=['first_name'])
    if not user.last_name and app.last_name:
        user.last_name = app.last_name
        user.save(update_fields=['last_name'])
    if changed:
        profile.save()
    return profile


def _estimate_tuition_amount(major, semester: Semester | None = None) -> int:
    """برآورد شهریه ترم: ثابت + ۱۲ واحد نظری + هزینه‌های جانبی."""
    if not major:
        return 0
    qs = TuitionStructure.objects.filter(major=major, is_active=True)
    if semester and semester.academic_year:
        ts = qs.filter(academic_year=semester.academic_year).first() or qs.order_by('-academic_year').first()
    else:
        ts = qs.order_by('-academic_year').first()
    if not ts:
        return 0
    return (
        int(ts.fixed_fee or 0)
        + int(ts.theory_fee or 0) * 12
        + int(ts.registration_fee or 0)
        + int(ts.insurance_fee or 0)
        + int(ts.card_fee or 0)
    )


def get_installment_plan(semester: Semester | None) -> TuitionInstallmentPlan | None:
    if not semester:
        return None
    return TuitionInstallmentPlan.objects.filter(
        academic_year=semester.academic_year, is_active=True
    ).first()


def _installment_ratios(semester: Semester | None = None):
    plan = get_installment_plan(semester)
    if plan:
        ratios = plan.ratios
        if sum(ratios) == 100:
            return ratios
    raw = getattr(settings, 'TUITION_INSTALLMENT_RATIOS', None) or DEFAULT_INSTALLMENT_RATIOS
    ratios = tuple(int(x) for x in raw)
    if len(ratios) != 3 or sum(ratios) != 100:
        return DEFAULT_INSTALLMENT_RATIOS
    return ratios


def _due_days(semester: Semester | None = None):
    plan = get_installment_plan(semester)
    if plan:
        return (plan.due_days_initial, plan.due_days_mid, plan.due_days_exam)
    return DEFAULT_DUE_DAYS


def approved_discount_percent(user: User, semester: Semester | None) -> int:
    if not semester:
        return 0
    total = (
        StudentDiscountClaim.objects.filter(
            student=user, semester=semester, status='approved'
        ).aggregate(s=Sum('percent'))['s']
        or 0
    )
    return min(int(total), 70)


def apply_discount(total: int, percent: int) -> int:
    if percent <= 0:
        return total
    return max(int(total * (100 - percent) // 100), 0)


def _split_amounts(total: int, semester: Semester | None = None) -> list[int]:
    r1, r2, r3 = _installment_ratios(semester)
    a1 = (total * r1) // 100
    a2 = (total * r2) // 100
    a3 = total - a1 - a2
    return [max(a1, 0), max(a2, 0), max(a3, 0)]


def _due_dates_for(semester: Semester | None) -> list:
    if not semester or not semester.start_date:
        return [None, None, None]
    days = _due_days(semester)
    return [semester.start_date + timedelta(days=d) for d in days]


def tuition_payments_qs(user: User, semester: Semester | None = None):
    """اقساط شهریه ترم — refunded حذف؛ بدون ترم یتیم با ترم فعال قاطی نشود."""
    qs = Payment.objects.filter(student=user, payment_type='tuition').exclude(status='refunded')
    if semester:
        qs = qs.filter(semester=semester)
    return qs


def _create_staged_payments(user, semester, major, amounts, due_dates):
    first = None
    for (no, stage, label), amount, due in zip(STAGE_META, amounts, due_dates):
        p = Payment.objects.create(
            student=user,
            payment_type='tuition',
            amount=amount,
            semester=semester,
            description=f'{label} — {major.name if major else ""} — {semester.name if semester else ""}',
            status='pending',
            installment_no=no,
            installment_stage=stage,
            due_date=due,
            method='online',
        )
        if first is None:
            first = p
    return first


def ensure_tuition_invoice(user: User, semester: Semester | None = None):
    """ساخت برنامه ۳ قسطی شهریه (با نسبت/سررسید سال تحصیلی و تخفیف تأییدشده)."""
    semester = semester or Semester.objects.filter(is_active=True).first()
    profile = sync_profile_from_application(user)
    major = profile.major
    gross = _estimate_tuition_amount(major, semester)
    if gross <= 0:
        return None

    discount_pct = approved_discount_percent(user, semester)
    total = apply_discount(gross, discount_pct)
    due_dates = _due_dates_for(semester)

    from django.db import transaction
    with transaction.atomic():
        existing = list(
            tuition_payments_qs(user, semester).select_for_update().order_by('installment_no', 'id')
        )
        staged_count = len([p for p in existing if (p.installment_no or 0) >= 1])
        has_exam = any(p.installment_stage == 'exam_card' for p in existing)

        if has_exam or staged_count >= 3:
            for p, due in zip(
                sorted(existing, key=lambda x: (x.installment_no is None, x.installment_no or 0)),
                due_dates,
            ):
                if due and not p.due_date and p.status in ('pending', 'failed'):
                    p.due_date = due
                    p.save(update_fields=['due_date'])
            return existing[0] if existing else None

        # تکمیل اقساط ناقص (۱ یا ۲ قسط)
        if staged_count in (1, 2) and not has_exam:
            present = {p.installment_stage for p in existing if p.installment_stage}
            amounts = _split_amounts(total, semester)
            for (no, stage, label), amount, due in zip(STAGE_META, amounts, due_dates):
                if stage not in present:
                    Payment.objects.create(
                        student=user,
                        payment_type='tuition',
                        amount=amount,
                        semester=semester,
                        description=f'{label} — {major.name if major else ""}',
                        status='pending',
                        installment_no=no,
                        installment_stage=stage,
                        due_date=due,
                        method='online',
                    )
            return tuition_payments_qs(user, semester).order_by('installment_no').first()

        # فاکتور قدیمی یک‌جا
        if len(existing) == 1 and not existing[0].installment_stage:
            old = existing[0]
            amounts = _split_amounts(total if old.status != 'paid' else (old.amount or total), semester)
            if old.status == 'paid':
                # تسویه یکجا → هر سه قسط paid
                old.amount = amounts[0]
                old.installment_no = 1
                old.installment_stage = 'initial'
                old.description = (old.description or '') + ' (تسویه یکجا)'
                old.save()
                for (no, stage, label), amount, due in zip(STAGE_META[1:], amounts[1:], due_dates[1:]):
                    Payment.objects.create(
                        student=user,
                        payment_type='tuition',
                        amount=amount,
                        semester=semester,
                        description=f'{label} — {major.name if major else ""} (تسویه یکجا)',
                        status='paid',
                        installment_no=no,
                        installment_stage=stage,
                        due_date=due,
                        method=old.method or 'online',
                        payment_date=old.payment_date,
                    )
                return old
            old.amount = amounts[0]
            old.installment_no = 1
            old.installment_stage = 'initial'
            old.due_date = due_dates[0]
            old.description = f'قسط ۱/۳ شهریه — {major.name if major else ""} — {semester.name if semester else ""}'
            if discount_pct:
                old.description += f' (تخفیف {discount_pct}٪)'
            old.save()
            for (no, stage, label), amount, due in zip(STAGE_META[1:], amounts[1:], due_dates[1:]):
                Payment.objects.create(
                    student=user,
                    payment_type='tuition',
                    amount=amount,
                    semester=semester,
                    description=f'{label} — {major.name if major else ""}',
                    status='pending',
                    installment_no=no,
                    installment_stage=stage,
                    due_date=due,
                    method='online',
                )
            return old

        if existing:
            return existing[0]

        amounts = _split_amounts(total, semester)
        return _create_staged_payments(user, semester, major, amounts, due_dates)


def reapply_discount_to_pending(user: User, semester: Semester | None = None) -> bool:
    """پس از تأیید تخفیف، مبالغ اقساط پرداخت‌نشده را بازتوزیع کند."""
    semester = semester or Semester.objects.filter(is_active=True).first()
    profile = sync_profile_from_application(user)
    gross = _estimate_tuition_amount(profile.major, semester)
    if gross <= 0:
        return False
    discount_pct = approved_discount_percent(user, semester)
    total = apply_discount(gross, discount_pct)
    qs = list(tuition_payments_qs(user, semester).order_by('installment_no', 'id'))
    staged = [p for p in qs if p.installment_stage]
    if len(staged) < 3:
        return False
    paid_amount = sum(p.amount for p in staged if p.status == 'paid')
    # فقط اقساط در انتظار/ناموفق — نه review (رسید ثبت‌شده)
    unpaid = [p for p in staged if p.status in ('pending', 'failed')]
    remaining_budget = max(total - paid_amount, 0)
    if not unpaid:
        return False
    # توزیع باقی‌مانده روی اقساط پرداخت‌نشده با نسبت برنامه
    ratios = _installment_ratios(semester)
    unpaid_ratios = []
    for p in unpaid:
        # #8: اگر installment_no=None باشد، از نسبت پیش‌فرض قسط اول استفاده نکن؛
        # به جایش ratio آن را صفر بگذار تا در توزیع نسبی تأثیر نگذارد.
        no = p.installment_no
        if no is not None and 1 <= no <= 3:
            idx = no - 1
            unpaid_ratios.append(ratios[idx])
        else:
            unpaid_ratios.append(0)
    ratio_sum = sum(unpaid_ratios) or 1
    allocated = 0
    for i, p in enumerate(unpaid):
        if i == len(unpaid) - 1:
            amount = remaining_budget - allocated
        else:
            amount = (remaining_budget * unpaid_ratios[i]) // ratio_sum
            allocated += amount
        p.amount = max(amount, 0)
        if discount_pct and f'تخفیف {discount_pct}' not in (p.description or ''):
            p.description = (p.description or '') + f' (تخفیف {discount_pct}٪)'
        p.save(update_fields=['amount', 'description'])
    return True


def tuition_first_paid(user: User, semester: Semester | None = None) -> bool:
    """قسط اول پرداخت شده → اجازه انتخاب واحد."""
    semester = semester or Semester.objects.filter(is_active=True).first()
    qs = tuition_payments_qs(user, semester)
    if qs.filter(installment_stage='initial', status='paid').exists():
        return True
    return qs.filter(status='paid', installment_stage='').exists()


def tuition_fully_settled(user: User, semester: Semester | None = None) -> bool:
    """همه اقساط پرداخت شده → صدور کارت ورود به جلسه / باز شدن نمرات."""
    semester = semester or Semester.objects.filter(is_active=True).first()
    qs = tuition_payments_qs(user, semester)
    staged = qs.exclude(installment_stage='')
    if staged.exists():
        # #1: همه قسط‌های staged باید paid باشند
        return not staged.exclude(status='paid').exists()
    # اگر هیچ قسط staged وجود ندارد، باید حداقل یک پرداخت paid با payment_type='tuition' باشد
    # و کل مبلغ پرداخت‌شده >= مبلغ کل باشد (نه فقط وجود هر پرداختی)
    paid_qs = qs.filter(status='paid')
    if not paid_qs.exists():
        return False
    # اگر ساختار اقساط وجود ندارد (سیستم قدیمی)، وجود هر پرداخت paid کافی نیست؛
    # مطمئن می‌شویم هیچ قسط pending/failed وجود ندارد
    return not qs.exclude(status__in=('paid', 'refunded')).exists()


def tuition_is_paid(user: User, semester: Semester | None = None) -> bool:
    """برای سازگاری: قسط اول (باز شدن انتخاب واحد)."""
    return tuition_first_paid(user, semester)


def ensure_exam_barcode(user: User, semester: Semester | None = None) -> str:
    """بارکد یکتا برای اسکن در جلسه امتحان."""
    semester = semester or Semester.objects.filter(is_active=True).first()
    if not semester or not tuition_fully_settled(user, semester):
        return ''
    gate = (
        tuition_payments_qs(user, semester)
        .filter(installment_stage='exam_card')
        .order_by('id')
        .first()
    )
    target = gate or tuition_payments_qs(user, semester).filter(status='paid').order_by('id').first()
    if not target:
        return ''
    if target.exam_barcode:
        return target.exam_barcode
    # #28: بارکد را بدون PII بساز — فقط از user.pk و semester.pk و یک salt مخفی
    secret = getattr(settings, 'SECRET_KEY', 'aab-barcode-salt')[:16]
    raw = f'{secret}-{user.pk}-{semester.pk}-exam'
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:10].upper()
    code = f'AAB{user.pk:05d}{semester.pk:04d}{digest}'
    target.exam_barcode = code
    target.save(update_fields=['exam_barcode'])
    return code


def tuition_summary(user: User, semester: Semester | None = None) -> dict:
    semester = semester or Semester.objects.filter(is_active=True).first()
    ensure_tuition_invoice(user, semester)
    qs = tuition_payments_qs(user, semester).order_by('installment_no', 'id')
    total = qs.aggregate(s=Sum('amount'))['s'] or 0
    paid = qs.filter(status='paid').aggregate(s=Sum('amount'))['s'] or 0
    discount_pct = approved_discount_percent(user, semester)
    plan = get_installment_plan(semester)
    return {
        'payments': list(qs),
        'total': total,
        'paid': paid,
        'remaining': max(total - paid, 0),
        'first_paid': tuition_first_paid(user, semester),
        'fully_settled': tuition_fully_settled(user, semester),
        'discount_percent': discount_pct,
        'plan': plan,
        'ratios': _installment_ratios(semester),
    }


def build_journey_status(user: User | None = None, national_id: str = '') -> dict:
    semester = Semester.objects.filter(is_active=True).first()
    nid = national_id
    profile = None
    summary = None
    if user and user.is_authenticated:
        profile = sync_profile_from_application(user)
        nid = profile.national_id or user.username
        summary = tuition_summary(user, semester)

    app = get_accepted_application(nid)
    has_account = False
    if user and user.is_authenticated:
        has_account = True
    elif nid:
        # #13: بررسی با national_id در پروفایل قابل اعتمادتر از username است،
        # چون ادمین ممکن است username را تغییر دهد.
        has_account = (
            UserProfile.objects.filter(national_id=nid, user__is_active=True).exists()
            or User.objects.filter(username=nid, is_active=True).exists()
        )

    first_paid = bool(summary and summary['first_paid'])
    fully = bool(summary and summary['fully_settled'])
    pending_payment = None
    enrolled_count = 0
    if user and user.is_authenticated:
        pending_payment = (
            tuition_payments_qs(user, semester)
            .filter(status__in=('pending', 'failed', 'review'))
            .order_by('installment_no')
            .first()
        )
        if semester:
            enrolled_count = Enrollment.objects.filter(
                student=user, semester=semester
            ).exclude(status='dropped').count()

    registration_open = bool(semester and semester.registration_open)

    steps = [
        {
            'key': 'accepted',
            'title': 'پذیرش نهایی',
            'done': bool(app),
            'hint': 'وضعیت درخواست شما پذیرفته شده است.' if app else 'هنوز پذیرش نهایی نشده.',
        },
        {
            'key': 'account',
            'title': 'ساخت / ورود به حساب دانشجویی',
            'done': has_account,
            'hint': 'با کد ملی وارد پنل دانشجو شوید.',
        },
        {
            'key': 'tuition',
            'title': 'پرداخت قسط اول شهریه',
            'done': first_paid,
            'hint': 'قسط اول برای باز شدن انتخاب واحد الزامی است؛ تسویه کامل برای کارت امتحان و مشاهده نمرات.',
        },
        {
            'key': 'registration',
            'title': 'انتخاب واحد / استاد و کلاس',
            'done': enrolled_count > 0,
            'hint': 'در بازه انتخاب واحد، درس و کلاس/استاد را انتخاب کنید.',
            'locked': not first_paid or not registration_open,
        },
        {
            'key': 'schedule',
            'title': 'برنامه کلاس',
            'done': enrolled_count > 0,
            'hint': 'پس از انتخاب واحد قابل مشاهده و پرینت است.',
            'locked': enrolled_count == 0,
        },
        {
            'key': 'exam_card',
            'title': 'کارت ورود به جلسه',
            'done': fully and enrolled_count > 0,
            'hint': 'پس از تسویه هر سه قسط شهریه صادر می‌شود.',
            'locked': not fully,
        },
    ]
    return {
        'application': app,
        'semester': semester,
        'registration_open': registration_open,
        'has_account': has_account,
        'tuition_paid': first_paid,
        'tuition_fully_settled': fully,
        'tuition_summary': summary,
        'pending_payment': pending_payment,
        'enrolled_count': enrolled_count,
        'steps': steps,
        'profile': profile,
    }
