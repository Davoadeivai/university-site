"""
گروه دسترسی «مدیر دانشگاه» — محدود به:
پذیرش، پیام‌های تماس، اخبار/گالری، اطلاعیه‌ها
"""
from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

STAFF_GROUP_NAME = 'مدیر دانشگاه'

# (app_label, model) — دسترسی view/add/change/delete
STAFF_MODEL_PERMS = [
    # پذیرش
    ('admissions', 'application'),
    ('admissions', 'admissioninfo'),
    ('admissions', 'tuitionstructure'),
    ('admissions', 'tuitiondiscount'),
    ('admissions', 'studentpayment'),
    # تماس
    ('contact', 'contactmessage'),
    ('contact', 'alumni'),
    # اخبار
    ('news', 'news'),
    ('news', 'category'),
    ('news', 'gallery'),
    # اطلاعیه‌های داخلی
    ('accounts', 'announcement'),
    # مشاهده پروفایل دانشجویان (برای خروجی لیست)
    ('accounts', 'userprofile'),
    # همکاری صنعتی (صفحه ارتباط با صنعت)
    ('research', 'industrypartnership'),
    # شهر بهنمیر
    ('core', 'cityinfo'),
    ('core', 'cityattraction'),
]


def ensure_staff_group() -> Group:
    """ساخت/به‌روزرسانی گروه مدیر دانشگاه با مجوزهای محدود."""
    group, _ = Group.objects.get_or_create(name=STAFF_GROUP_NAME)
    wanted = []
    for app_label, model in STAFF_MODEL_PERMS:
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            continue
        for action in ('view', 'add', 'change', 'delete'):
            codename = f'{action}_{model}'
            try:
                wanted.append(Permission.objects.get(content_type=ct, codename=codename))
            except Permission.DoesNotExist:
                continue
    group.permissions.set(wanted)
    return group


def sync_user_role_access(user, role: str) -> None:
    """
    همگام‌سازی دسترسی جنگو با نقش پروفایل:
    - staff  → is_staff=True، عضو گروه مدیر دانشگاه، بدون superuser
    - admin  → is_staff=True، is_superuser=True
    - سایر   → حذف از گروه مدیر؛ staff/superuser دست نخورده نمی‌ماند اگر قبلاً فقط به‌خاطر نقش بود
    """
    from django.contrib.auth.models import User

    if not isinstance(user, User):
        return

    group = ensure_staff_group()

    if role == 'admin':
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=['is_staff', 'is_superuser'])
        user.groups.remove(group)
        return

    if role == 'staff':
        user.is_staff = True
        user.is_superuser = False
        user.save(update_fields=['is_staff', 'is_superuser'])
        user.groups.add(group)
        return

    # دانشجو / استاد: از گروه مدیر خارج شو؛ پرچم staff را فقط اگر عضو گروه مدیر بود خاموش کن
    was_manager = user.groups.filter(name=STAFF_GROUP_NAME).exists()
    user.groups.remove(group)
    if was_manager and not user.is_superuser:
        user.is_staff = False
        user.save(update_fields=['is_staff'])
