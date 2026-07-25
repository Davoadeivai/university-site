"""مسیر پس از پذیرش: همگام‌سازی پروفایل، اقساط شهریه، وضعیت مراحل."""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q, Sum

from admissions.models import Application, TuitionStructure
from accounts.models import UserProfile

from .models import Enrollment, Payment, Semester

# نسبت اقساط پیش‌فرض: اول / میانی / کارت امتحان (جمع = ۱۰۰)
DEFAULT_INSTALLMENT_RATIOS = (40, 30, 30)
STAGE_META = (
    (1, 'initial', 'قسط اول — پیش‌پرداخت ثبت‌نام / انتخاب واحد'),
    (2, 'mid', 'قسط دوم — میانی ترم'),
    (3, 'exam_card', 'قسط سوم — تسویه برای کارت ورود به جلسه'),
)


def get_accepted_application(national_id: str) -> Application | None:
    nid = (national_id or '').strip()
    if not nid:
        return None
    return (
        Application.objects.filter(national_id=nid, status='accepted')
        .select_related('desired_major', 'desired_major2')
        .order_by('-id')
        .first()
    )


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
    if app.desired_major_id and profile.major_id != app.desired_major_id:
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


def _estimate_tuition_amount(major) -> int:
    if not major:
        return 0
    ts = TuitionStructure.objects.filter(major=major, is_active=True).order_by('-academic_year').first()
    if not ts:
        return 0
    return int(ts.fixed_fee or 0) + int(ts.theory_fee or 0) * 12


def _installment_ratios():
    raw = getattr(settings, 'TUITION_INSTALLMENT_RATIOS', None) or DEFAULT_INSTALLMENT_RATIOS
    ratios = tuple(int(x) for x in raw)
    if len(ratios) != 3 or sum(ratios) != 100:
        return DEFAULT_INSTALLMENT_RATIOS
    return ratios


def _split_amounts(total: int) -> list[int]:
    r1, r2, r3 = _installment_ratios()
    a1 = (total * r1) // 100
    a2 = (total * r2) // 100
    a3 = total - a1 - a2
    return [max(a1, 0), max(a2, 0), max(a3, 0)]


def tuition_payments_qs(user: User, semester: Semester | None = None):
    qs = Payment.objects.filter(student=user, payment_type='tuition').exclude(status='refunded')
    if semester:
        qs = qs.filter(Q(semester=semester) | Q(semester__isnull=True))
    return qs


def ensure_tuition_invoice(user: User, semester: Semester | None = None):
    """ساخت برنامه ۳ قسطی شهریه برای همه رشته‌ها/مقاطع (در صورت نبود)."""
    semester = semester or Semester.objects.filter(is_active=True).first()
    profile = sync_profile_from_application(user)
    major = profile.major
    total = _estimate_tuition_amount(major)
    if total <= 0:
        return None

    existing = list(
        tuition_payments_qs(user, semester).order_by('installment_no', 'id')
    )
    # اگر قبلاً سه قسط ساخته شده
    if any(p.installment_stage == 'exam_card' for p in existing) or (
        len([p for p in existing if p.installment_no]) >= 3
    ):
        return existing[0] if existing else None

    # فاکتور قدیمی یک‌جا: اگر پرداخت شده = تسویه کامل؛ اگر در انتظار = تبدیل به ۳ قسط
    if len(existing) == 1 and not existing[0].installment_stage:
        old = existing[0]
        if old.status == 'paid':
            old.installment_no = 1
            old.installment_stage = 'initial'
            old.description = (old.description or '') + ' (تسویه یکجا — معادل کامل)'
            old.save(update_fields=['installment_no', 'installment_stage', 'description'])
            # قسط ۲ و ۳ را paid با مبلغ ۰ نساز؛ برای کارت امتحان، fully_settled اگر مبلغ پرداختی >= total
            return old
        amounts = _split_amounts(old.amount or total)
        old.amount = amounts[0]
        old.installment_no = 1
        old.installment_stage = 'initial'
        old.description = f'قسط ۱/۳ شهریه — {major.name if major else ""} — {semester.name if semester else ""}'
        old.save()
        for (no, stage, label), amount in zip(STAGE_META[1:], amounts[1:]):
            Payment.objects.create(
                student=user,
                payment_type='tuition',
                amount=amount,
                semester=semester,
                description=f'{label} — {major.name if major else ""}',
                status='pending',
                installment_no=no,
                installment_stage=stage,
            )
        return old

    if existing:
        return existing[0]

    amounts = _split_amounts(total)
    first = None
    for (no, stage, label), amount in zip(STAGE_META, amounts):
        p = Payment.objects.create(
            student=user,
            payment_type='tuition',
            amount=amount,
            semester=semester,
            description=f'{label} — {major.name if major else ""} — {semester.name if semester else ""}',
            status='pending',
            installment_no=no,
            installment_stage=stage,
        )
        if first is None:
            first = p
    return first


def tuition_first_paid(user: User, semester: Semester | None = None) -> bool:
    """قسط اول پرداخت شده → اجازه انتخاب واحد."""
    semester = semester or Semester.objects.filter(is_active=True).first()
    qs = tuition_payments_qs(user, semester)
    if qs.filter(installment_stage='initial', status='paid').exists():
        return True
    # فاکتور قدیمی یکجا (بدون مرحله)
    return qs.filter(status='paid', installment_stage='').exists()


def tuition_fully_settled(user: User, semester: Semester | None = None) -> bool:
    """همه اقساط پرداخت شده → صدور کارت ورود به جلسه."""
    semester = semester or Semester.objects.filter(is_active=True).first()
    qs = tuition_payments_qs(user, semester)
    staged = qs.exclude(installment_stage='')
    if staged.exists():
        pending = staged.exclude(status='paid')
        return not pending.exists()
    # فاکتور قدیمی: یک پرداخت موفق کافی است
    return qs.filter(status='paid').exists()


def tuition_is_paid(user: User, semester: Semester | None = None) -> bool:
    """برای سازگاری: قسط اول (باز شدن انتخاب واحد)."""
    return tuition_first_paid(user, semester)


def tuition_summary(user: User, semester: Semester | None = None) -> dict:
    semester = semester or Semester.objects.filter(is_active=True).first()
    ensure_tuition_invoice(user, semester)
    qs = tuition_payments_qs(user, semester).order_by('installment_no', 'id')
    total = qs.aggregate(s=Sum('amount'))['s'] or 0
    paid = qs.filter(status='paid').aggregate(s=Sum('amount'))['s'] or 0
    return {
        'payments': list(qs),
        'total': total,
        'paid': paid,
        'remaining': max(total - paid, 0),
        'first_paid': tuition_first_paid(user, semester),
        'fully_settled': tuition_fully_settled(user, semester),
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
        has_account = User.objects.filter(username=nid).exists() or UserProfile.objects.filter(national_id=nid).exists()

    first_paid = bool(summary and summary['first_paid'])
    fully = bool(summary and summary['fully_settled'])
    pending_payment = None
    enrolled_count = 0
    if user and user.is_authenticated:
        pending_payment = tuition_payments_qs(user, semester).filter(status='pending').order_by('installment_no').first()
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
            'hint': 'قسط اول برای باز شدن انتخاب واحد الزامی است؛ تسویه کامل برای کارت امتحان.',
        },
        {
            'key': 'registration',
            'title': 'انتخاب واحد / استاد و کلاس',
            'done': enrolled_count > 0,
            'hint': 'در بازه انتخاب واحد، درس و کلاس/استاد را انتخاب کنید.',
            'locked': not first_paid,
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
