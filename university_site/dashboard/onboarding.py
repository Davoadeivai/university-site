"""مسیر پس از پذیرش: همگام‌سازی پروفایل، فاکتور شهریه، وضعیت مراحل."""
from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Q

from admissions.models import Application, TuitionStructure
from accounts.models import UserProfile

from .models import Enrollment, Payment, Semester


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
    # پیش‌فرض: شهریه ثابت + ۱۲ واحد نظری (قابل تنظیم بعدی)
    return int(ts.fixed_fee or 0) + int(ts.theory_fee or 0) * 12


def ensure_tuition_invoice(user: User, semester: Semester | None = None) -> Payment | None:
    """اگر فاکتور شهریه ترم فعال نباشد، یکی بساز."""
    semester = semester or Semester.objects.filter(is_active=True).first()
    profile = sync_profile_from_application(user)
    major = profile.major
    amount = _estimate_tuition_amount(major)
    if amount <= 0:
        return None

    existing = Payment.objects.filter(
        student=user,
        payment_type='tuition',
        semester=semester,
    ).exclude(status='refunded').first()
    if existing:
        return existing

    desc = f'شهریه ترم {semester.name if semester else ""} — {major.name if major else "رشته"}'
    return Payment.objects.create(
        student=user,
        payment_type='tuition',
        amount=amount,
        semester=semester,
        description=desc.strip(),
        status='pending',
    )


def tuition_is_paid(user: User, semester: Semester | None = None) -> bool:
    semester = semester or Semester.objects.filter(is_active=True).first()
    qs = Payment.objects.filter(student=user, payment_type='tuition', status='paid')
    if semester:
        qs = qs.filter(Q(semester=semester) | Q(semester__isnull=True))
    return qs.exists()


def build_journey_status(user: User | None = None, national_id: str = '') -> dict:
    """وضعیت مراحل مسیر دانشجو برای صفحه پیگیری / داشبورد."""
    semester = Semester.objects.filter(is_active=True).first()
    nid = national_id
    profile = None
    if user and user.is_authenticated:
        profile = sync_profile_from_application(user)
        nid = profile.national_id or user.username
        ensure_tuition_invoice(user, semester)

    app = get_accepted_application(nid)
    has_account = False
    if user and user.is_authenticated:
        has_account = True
    elif nid:
        has_account = User.objects.filter(username=nid).exists() or UserProfile.objects.filter(national_id=nid).exists()

    paid = False
    pending_payment = None
    enrolled_count = 0
    if user and user.is_authenticated:
        paid = tuition_is_paid(user, semester)
        pending_payment = Payment.objects.filter(
            student=user, payment_type='tuition', status='pending', semester=semester
        ).first()
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
            'title': 'پرداخت شهریه ترم',
            'done': paid,
            'hint': 'پس از ورود، فاکتور شهریه در بخش پرداخت‌ها ساخته می‌شود.',
        },
        {
            'key': 'registration',
            'title': 'انتخاب واحد',
            'done': enrolled_count > 0,
            'hint': 'در بازه انتخاب واحد، دروس ترم را انتخاب کنید.',
            'locked': not paid,
        },
        {
            'key': 'schedule',
            'title': 'برنامه کلاس و لیست استاد',
            'done': enrolled_count > 0,
            'hint': 'بعد از انتخاب واحد، استاد و زمان کلاس نمایش داده می‌شود.',
            'locked': enrolled_count == 0,
        },
    ]
    return {
        'application': app,
        'semester': semester,
        'registration_open': registration_open,
        'has_account': has_account,
        'tuition_paid': paid,
        'pending_payment': pending_payment,
        'enrolled_count': enrolled_count,
        'steps': steps,
        'profile': profile,
    }
