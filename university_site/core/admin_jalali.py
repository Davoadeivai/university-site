"""کمک‌کننده‌های نمایش تاریخ شمسی در ادمین Django."""
from django.contrib import admin

from core.jalali import format_jalali_date, format_jalali_datetime


class JalaliAdminMixin:
    """برای جایگزینی ستون‌های تاریخ میلادی در list_display."""

    @admin.display(description='تاریخ ایجاد', ordering='created_at')
    def created_jalali(self, obj):
        return format_jalali_datetime(getattr(obj, 'created_at', None))

    @admin.display(description='تاریخ انتشار', ordering='published_at')
    def published_jalali(self, obj):
        val = getattr(obj, 'published_at', None)
        if hasattr(val, 'hour'):
            return format_jalali_datetime(val)
        return format_jalali_date(val, 'short')

    @admin.display(description='به‌روزرسانی', ordering='updated_at')
    def updated_jalali(self, obj):
        return format_jalali_datetime(getattr(obj, 'updated_at', None))
