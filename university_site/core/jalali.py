"""ابزارهای مشترک تاریخ شمسی (جلالی) برای کل پروژه."""
from __future__ import annotations

from datetime import date, datetime

import jdatetime
from django.utils import timezone as dj_tz

PERSIAN_MONTHS = [
    '', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
]
PERSIAN_WEEKDAYS = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه', 'یکشنبه']
PERSIAN_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')


def to_persian_digits(value: str) -> str:
    return str(value).translate(PERSIAN_DIGITS)


def _localize_dt(value: datetime) -> datetime:
    if dj_tz.is_aware(value):
        return dj_tz.localtime(value)
    return value


def to_jdatetime(value):
    """Convert date/datetime to jdatetime.datetime (local time)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        value = _localize_dt(value)
        return jdatetime.datetime.fromgregorian(datetime=value)
    if isinstance(value, date):
        return jdatetime.datetime.fromgregorian(date=value)
    return None


def format_jalali_date(value, fmt: str = 'long', persian_digits: bool = True) -> str:
    """
    fmt:
      long  → ۱۴ اردیبهشت ۱۴۰۴
      short → ۱۴۰۴/۰۲/۱۴
      day / month / year / full
    """
    if not value:
        return ''
    jdt = to_jdatetime(value)
    if jdt is None:
        return str(value)
    j = jdt.date() if hasattr(jdt, 'date') else jdt

    def dig(s):
        return to_persian_digits(s) if persian_digits else s

    if fmt == 'short':
        return dig(f'{j.year:04d}/{j.month:02d}/{j.day:02d}')
    if fmt == 'day':
        return dig(str(j.day))
    if fmt == 'month':
        return PERSIAN_MONTHS[j.month]
    if fmt == 'year':
        return dig(str(j.year))
    if fmt == 'full':
        wd = PERSIAN_WEEKDAYS[j.weekday()]
        return f'{wd} {dig(str(j.day))} {PERSIAN_MONTHS[j.month]} {dig(str(j.year))}'
    return f'{dig(str(j.day))} {PERSIAN_MONTHS[j.month]} {dig(str(j.year))}'


def format_jalali_datetime(value, persian_digits: bool = True) -> str:
    """۱۴۰۴/۰۲/۱۴ - ۱۴:۳۵"""
    if not value:
        return ''
    jdt = to_jdatetime(value)
    if jdt is None:
        return format_jalali_date(value, 'short', persian_digits=persian_digits)
    date_str = f'{jdt.year:04d}/{jdt.month:02d}/{jdt.day:02d}'
    time_str = f'{jdt.hour:02d}:{jdt.minute:02d}'
    out = f'{date_str} - {time_str}'
    return to_persian_digits(out) if persian_digits else out


def jalali_now_stamp(fmt: str = '%Y%m%d') -> str:
    """برای نام فایل — ارقام انگلیسی شمسی."""
    return jdatetime.datetime.now().strftime(fmt)
