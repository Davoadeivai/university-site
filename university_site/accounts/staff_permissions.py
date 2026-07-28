"""
گروه دسترسی «مدیر دانشگاه» — محدود به:
پذیرش، پیام‌های تماس، اخبار/گالری، اطلاعیه‌ها
"""
from __future__ import annotations

import logging

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

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
    - staff / admin → is_staff=True و عضویت در گروه «مدیر دانشگاه»
    - سایر نقش‌ها   → خروج از گروه مدیر؛ is_staff فقط اگر صرفاً به‌خاطر نقش روشن بود خاموش می‌شود

    امنیت — این تابع عمداً هرگز `is_superuser` را نمی‌نویسد، نه روشن و نه خاموش:

    * نوشتن True یعنی هر کسی که مجوز ویرایش پروفایل دارد (گروه «مدیر دانشگاه»
      این مجوز را دارد) می‌تواند نقش خودش را روی admin بگذارد و superuser شود.
    * نوشتن False یعنی ذخیرهٔ سادهٔ پروفایلِ یک superuser واقعی او را از سیستم
      بیرون می‌اندازد، و یک کاربر staff می‌تواند با تغییر نقشِ دیگران دسترسی
      مدیر اصلی را سلب کند.

    اعطا و سلب superuser باید صراحتاً توسط یک superuser موجود یا با
    `manage.py createsuperuser` انجام شود. موارد نیازمند رسیدگی دستی لاگ می‌شوند.
    """
    from django.contrib.auth.models import User

    if not isinstance(user, User):
        return

    group = ensure_staff_group()

    if role in ('admin', 'staff'):
        if role == 'admin' and not user.is_superuser:
            logger.warning(
                'نقش «admin» برای کاربر %s (pk=%s) ثبت شد اما superuser اعطا نشد. '
                'در صورت نیاز باید دستی توسط یک superuser موجود انجام شود.',
                user.username, user.pk,
            )
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=['is_staff'])
        user.groups.add(group)
        return

    # دانشجو / استاد: از گروه مدیر خارج شو؛ پرچم staff را فقط اگر عضو گروه مدیر بود خاموش کن
    if user.is_superuser:
        logger.warning(
            'کاربر %s (pk=%s) نقش «%s» گرفت ولی همچنان superuser است. '
            'سلب دسترسی superuser باید دستی انجام شود.',
            user.username, user.pk, role,
        )
    was_manager = user.groups.filter(name=STAFF_GROUP_NAME).exists()
    user.groups.remove(group)
    if was_manager and not user.is_superuser:
        user.is_staff = False
        user.save(update_fields=['is_staff'])
