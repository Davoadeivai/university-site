"""اطلاع‌رسانی پیامکی رویدادهای سامانه (پذیرش، انتخاب واحد، پروفایل، اخبار)."""
from __future__ import annotations

import logging

from django.conf import settings

from core.sms import normalize_phone, send_sms

logger = logging.getLogger('django')

# حداکثر طول تقریبی پیامک فارسی (چند بخشی نشود)
_SMS_MAX_LEN = 200

_ANNOUNCEMENT_TARGET_ROLES = {
    'all': ['student', 'professor', 'staff', 'admin'],
    'students': ['student'],
    'professors': ['professor'],
    'staff': ['staff', 'admin'],
}


def _site_label() -> str:
    return getattr(settings, 'SMS_SITE_LABEL', '') or 'موسسه آموزش عالی علامه امینی بهنمیر'


def _clip(text: str, max_len: int = _SMS_MAX_LEN) -> str:
    text = (text or '').strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + '…'


def notify_phone(phone: str, message: str) -> bool:
    """ارسال یک پیامک اطلاع‌رسانی به یک شماره."""
    phone = normalize_phone(phone)
    if not phone or len(phone) < 10:
        return False
    return send_sms(phone, _clip(message))


def phone_from_user(user) -> str:
    """شماره موبایل کاربر از پروفایل."""
    if not user:
        return ''
    try:
        return normalize_phone(user.profile.phone or '')
    except Exception:
        return ''


def phones_for_roles(roles: list[str]) -> list[str]:
    """شماره‌های یکتا برای نقش‌های داده‌شده."""
    from accounts.models import UserProfile

    qs = (
        UserProfile.objects.filter(role__in=roles)
        .exclude(phone='')
        .values_list('phone', flat=True)
    )
    seen: set[str] = set()
    out: list[str] = []
    for raw in qs:
        phone = normalize_phone(raw)
        if phone and phone not in seen:
            seen.add(phone)
            out.append(phone)
    return out


def notify_phones(phones: list[str], message: str) -> int:
    """ارسال گروهی؛ تعداد ارسال موفق را برمی‌گرداند."""
    msg = _clip(message)
    ok = 0
    for phone in phones:
        if notify_phone(phone, msg):
            ok += 1
    return ok


def notify_application_created(application) -> bool:
    label = _site_label()
    msg = (
        f'{label}: درخواست پذیرش شما ثبت شد. '
        f'کد رهگیری: {application.tracking_code}'
    )
    return notify_phone(application.phone, msg)


def notify_application_status(application) -> bool:
    label = _site_label()
    status = application.get_status_display()
    msg = (
        f'{label}: وضعیت پذیرش شما به «{status}» تغییر یافت. '
        f'کد رهگیری: {application.tracking_code}'
    )
    return notify_phone(application.phone, msg)


def notify_enrollment_created(enrollment) -> bool:
    label = _site_label()
    course = getattr(enrollment.course, 'name', 'درس')
    semester = getattr(enrollment.semester, 'name', '')
    msg = f'{label}: انتخاب واحد ثبت شد — {course}'
    if semester:
        msg += f' ({semester})'
    return notify_phone(phone_from_user(enrollment.student), msg)


def notify_enrollment_status(enrollment) -> bool:
    label = _site_label()
    course = getattr(enrollment.course, 'name', 'درس')
    status = enrollment.get_status_display()
    msg = f'{label}: وضعیت درس «{course}» به «{status}» تغییر یافت.'
    return notify_phone(phone_from_user(enrollment.student), msg)


def notify_profile_created(profile) -> bool:
    label = _site_label()
    name = ''
    if profile.user_id:
        name = profile.user.get_full_name() or profile.user.username
    msg = f'{label}: حساب کاربری شما با موفقیت ساخته شد.'
    if name:
        msg = f'{label}: {name} عزیز، حساب کاربری شما ساخته شد.'
    return notify_phone(profile.phone, msg)


def notify_profile_updated(profile, changed_fields: list[str]) -> bool:
    if not changed_fields:
        return False
    label = _site_label()
    field_labels = {
        'phone': 'شماره موبایل',
        'student_id': 'شماره دانشجویی',
        'department': 'دانشکده',
        'national_id': 'کد ملی',
        'role': 'نقش',
        'bio': 'بیوگرافی',
        'avatar': 'عکس پروفایل',
        'birth_date': 'تاریخ تولد',
    }
    names = [field_labels.get(f, f) for f in changed_fields]
    msg = f'{label}: پروفایل شما به‌روز شد ({"، ".join(names)}).'
    return notify_phone(profile.phone, msg)


def notify_announcement(announcement) -> int:
    """اطلاعیه داخلی داشبورد → مخاطبان هدف."""
    roles = _ANNOUNCEMENT_TARGET_ROLES.get(announcement.target, ['student'])
    phones = phones_for_roles(roles)
    if not phones:
        return 0
    label = _site_label()
    urgent = 'فوری — ' if announcement.is_urgent else ''
    msg = f'{label}: {urgent}اطلاعیه جدید — {announcement.title}'
    return notify_phones(phones, msg)


def notify_news_published(news) -> int:
    """خبر/اطلاعیه عمومی منتشرشده → دانشجویان (و در صورت نیاز همه)."""
    # اخبار عمومی سایت برای دانشجویان ارسال می‌شود
    phones = phones_for_roles(['student', 'professor', 'staff'])
    if not phones:
        return 0
    label = _site_label()
    type_label = news.get_news_type_display() if hasattr(news, 'get_news_type_display') else 'خبر'
    msg = f'{label}: {type_label} جدید — {news.title}'
    return notify_phones(phones, msg)
