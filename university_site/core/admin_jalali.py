"""کمک‌کننده‌های نمایش تاریخ شمسی در ادمین Django."""
from __future__ import annotations

from django.contrib import admin

from core.jalali import (
    format_jalali_date,
    format_jalali_datetime,
    gregorian_years_in_text as _gregorian_years_in_text,
    jalali_year_range as _jalali_year_range,
)


class JalaliAdminMixin:
    """برای جایگزینی ستون‌های تاریخ میلادی در list_display."""

    @admin.display(description='تاریخ ایجاد', ordering='created_at')
    def created_jalali(self, obj):
        return format_jalali_datetime(getattr(obj, 'created_at', None)) or '—'

    @admin.display(description='تاریخ انتشار', ordering='published_at')
    def published_jalali(self, obj):
        val = getattr(obj, 'published_at', None)
        if hasattr(val, 'hour'):
            return format_jalali_datetime(val) or '—'
        return format_jalali_date(val, 'short') or '—'

    @admin.display(description='به‌روزرسانی', ordering='updated_at')
    def updated_jalali(self, obj):
        return format_jalali_datetime(getattr(obj, 'updated_at', None)) or '—'

    @admin.display(description='تاریخ شروع', ordering='start_date')
    def start_date_jalali(self, obj):
        return format_jalali_date(getattr(obj, 'start_date', None), 'short') or '—'

    @admin.display(description='تاریخ پایان', ordering='end_date')
    def end_date_jalali(self, obj):
        return format_jalali_date(getattr(obj, 'end_date', None), 'short') or '—'

    @admin.display(description='تاریخ', ordering='date')
    def date_jalali(self, obj):
        val = getattr(obj, 'date', None)
        if hasattr(val, 'hour'):
            return format_jalali_datetime(val) or '—'
        return format_jalali_date(val, 'short') or '—'

    @admin.display(description='مهلت', ordering='due_date')
    def due_date_jalali(self, obj):
        val = getattr(obj, 'due_date', None)
        if hasattr(val, 'hour'):
            return format_jalali_datetime(val) or '—'
        return format_jalali_date(val, 'short') or '—'

    @admin.display(description='تاریخ پرداخت', ordering='payment_date')
    def payment_date_jalali(self, obj):
        return format_jalali_datetime(getattr(obj, 'payment_date', None)) or '—'

    @admin.display(description='ثبت‌نام', ordering='enrolled_at')
    def enrolled_jalali(self, obj):
        return format_jalali_datetime(getattr(obj, 'enrolled_at', None)) or '—'

    @admin.display(description='سال تحصیلی', ordering='academic_year')
    def academic_year_jalali(self, obj):
        return _jalali_year_range(getattr(obj, 'academic_year', '') or '')

    @admin.display(description='نام ترم', ordering='name')
    def name_jalali(self, obj):
        return _gregorian_years_in_text(getattr(obj, 'name', '') or '') or '—'

    @admin.display(description='مهلت', ordering='deadline')
    def deadline_jalali(self, obj):
        val = getattr(obj, 'deadline', None)
        if hasattr(val, 'hour'):
            return format_jalali_datetime(val) or '—'
        return format_jalali_date(val, 'short') or '—'

    @admin.display(description='انقضا', ordering='expires_at')
    def expires_jalali(self, obj):
        return format_jalali_datetime(getattr(obj, 'expires_at', None)) or '—'

    @admin.display(description='تاریخ پرداخت', ordering='paid_at')
    def paid_at_jalali(self, obj):
        return format_jalali_datetime(getattr(obj, 'paid_at', None)) or '—'
