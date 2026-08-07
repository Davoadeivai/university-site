"""فیلد فرم برای وارد کردن تاریخ به شمسی.

مشکلی که حل می‌کند
──────────────────
فهرست‌های ادمین از قبل تاریخ‌ها را شمسی نشان می‌دادند، ولی فرم ویرایش
همان `DateField` خام جنگو بود: کارمند آموزش باید «۳۱ شهریور ۱۴۰۵» را
در ذهنش به `2026-09-22` تبدیل می‌کرد و همان را تایپ می‌کرد. هر خطای
تبدیل مستقیم روی تقویم آموزشی سایت می‌نشست.

اینجا ورودی و نمایش هر دو شمسی‌اند و تبدیل به میلادی سمت سرور انجام
می‌شود. چیزی در دیتابیس عوض نمی‌شود — ستون همان `DateField` میلادی
می‌ماند، پس مرتب‌سازی، فیلتر و مقایسهٔ تاریخ‌ها دست‌نخورده است.

هرچه کاربر بنویسد پذیرفته می‌شود
────────────────────────────────
ارقام فارسی و عربی، جداکنندهٔ `/` یا `-` یا `.`، با صفر ابتدایی یا
بدون آن. «۱۴۰۵/۶/۳۱» و «1405-06-31» هر دو یک تاریخ‌اند.
"""
from __future__ import annotations

import re

import jdatetime
from django import forms
from django.core.exceptions import ValidationError

from core.jalali import to_persian_digits

# ارقام فارسی و عربی → لاتین
_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
_PARTS = re.compile(r'^(\d{3,4})\D(\d{1,2})\D(\d{1,2})$')


def parse_jalali(text: str):
    """«۱۴۰۵/۰۶/۳۱» → datetime.date میلادی. ورودی نامعتبر → None."""
    if not text:
        return None
    cleaned = str(text).translate(_DIGITS).strip()
    cleaned = cleaned.replace('،', '/').replace(' ', '')
    match = _PARTS.match(cleaned)
    if not match:
        return None
    year, month, day = (int(g) for g in match.groups())
    # سال دورقمی معنا ندارد و سال میلادی هم اشتباه رایج است
    if year < 1200 or year > 1600:
        return None
    try:
        return jdatetime.date(year, month, day).togregorian()
    except ValueError:
        return None


class JalaliDateWidget(forms.TextInput):
    """ورودی متنی که مقدار ذخیره‌شده را شمسی نشان می‌دهد."""

    def __init__(self, attrs=None):
        defaults = {
            'placeholder': 'مثال: ۱۴۰۵/۰۶/۳۱',
            'dir': 'ltr',
            'style': 'text-align:center;max-width:12rem;',
            'autocomplete': 'off',
            'inputmode': 'numeric',
        }
        defaults.update(attrs or {})
        super().__init__(defaults)

    def format_value(self, value):
        if not value:
            return ''
        # مقدار ممکن است date باشد (از دیتابیس) یا رشتهٔ بازگشتی از
        # فرمی که اعتبارسنجی‌اش شکسته — دومی باید همان‌طور برگردد تا
        # کاربر نوشتهٔ خودش را ببیند، نه یک فیلد خالی.
        if hasattr(value, 'year') and hasattr(value, 'month'):
            jalali = jdatetime.date.fromgregorian(date=value)
            return to_persian_digits('%04d/%02d/%02d' % (
                jalali.year, jalali.month, jalali.day))
        return str(value)


class JalaliDateField(forms.DateField):
    widget = JalaliDateWidget
    default_error_messages = {
        'invalid': 'تاریخ را به شمسی و در قالب ۱۴۰۵/۰۶/۳۱ بنویسید.',
    }

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if hasattr(value, 'year'):        # از قبل date است
            return value
        parsed = parse_jalali(value)
        if parsed is None:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        return parsed


class JalaliAdminFormMixin:
    """همهٔ DateFieldهای فرم را به ورودی شمسی تبدیل می‌کند.

    به‌جای نام‌بردن تک‌تک فیلدها در هر ModelAdmin، خودِ فرم را عوض
    می‌کند تا اضافه‌شدن یک تاریخ تازه به مدل، خودبه‌خود پوشش بگیرد.
    """

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        from django.db import models as db_models
        if isinstance(db_field, db_models.DateField) and not isinstance(
                db_field, db_models.DateTimeField):
            kwargs.setdefault('form_class', JalaliDateField)
            field = super().formfield_for_dbfield(db_field, request, **kwargs)
            existing = (field.help_text or '').strip()
            note = 'تاریخ شمسی — مثال: ۱۴۰۵/۰۶/۳۱'
            field.help_text = ('%s<br>%s' % (existing, note)) if existing else note
            return field
        return super().formfield_for_dbfield(db_field, request, **kwargs)
