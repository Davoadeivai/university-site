"""پاک‌سازی کش context سراسری هنگام تغییر محتوای آن.

`core.context_processors.global_context` نتیجه‌اش را ۶۰ ثانیه کش می‌کند.
بدون این ماژول، ادمین پس از پنهان‌کردن یک بخش یا تغییر عنوان/تصویر تا یک
دقیقه تغییر را نمی‌دید — و روی سرور که هر worker کش جدا دارد، کاربران
مختلف حالت‌های متفاوتی می‌دیدند.

اینجا هر مدلی که به آن context خورد می‌دهد، با ذخیره یا حذف، کلید کش را
باطل می‌کند تا تغییر بلافاصله دیده شود.
"""
from __future__ import annotations

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

GLOBAL_CONTEXT_KEY = 'global_context_v1'


def clear_global_context(*args, **kwargs) -> None:
    cache.delete(GLOBAL_CONTEXT_KEY)


def register() -> None:
    """اتصال سیگنال‌ها. از AppConfig.ready صدا زده می‌شود."""
    from academics.models import AcademicGroup, Department
    from accounts.models import Announcement
    from core.models import HomeFeature, HomeSection, QuickLink, SiteSettings
    from news.models import News

    watched = [
        SiteSettings, QuickLink, HomeSection, HomeFeature,
        News, Announcement, AcademicGroup, Department,
    ]
    for model in watched:
        uid = f'core.clear_global_ctx.{model._meta.label_lower}'
        post_save.connect(
            clear_global_context, sender=model,
            dispatch_uid=f'{uid}.save', weak=False,
        )
        post_delete.connect(
            clear_global_context, sender=model,
            dispatch_uid=f'{uid}.delete', weak=False,
        )
