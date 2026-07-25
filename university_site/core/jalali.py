"""ابزارهای مشترک تاریخ شمسی (جلالی) برای کل پروژه."""
from __future__ import annotations

import re
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


def g2j_year(year: int) -> int:
    """تقریب سال شمسی از سال میلادی (حوالی نوروز)."""
    return jdatetime.date.fromgregorian(date=date(year, 3, 21)).year


def jalali_year_range(text: str) -> str:
    """تبدیل رشته سال تحصیلی مثل 2026-2027 به ۱۴۰۵-۱۴۰۶."""
    if not text:
        return text
    m = re.match(r'^\s*(\d{4})\s*[-–/]\s*(\d{4})\s*$', str(text))
    if not m:
        return gregorian_years_in_text(str(text))
    y1, y2 = int(m.group(1)), int(m.group(2))
    if y1 >= 1300 and y1 < 1600:
        return to_persian_digits(str(text))
    try:
        return to_persian_digits(f'{g2j_year(y1)}-{g2j_year(y2)}')
    except Exception:
        return str(text)


def gregorian_years_in_text(text: str) -> str:
    """تبدیل سال‌های چهاررقمی میلادی داخل متن (مثل «ترم جاری 2026»)."""
    if not text:
        return text

    def repl(m):
        y = int(m.group(0))
        if 1300 <= y < 1600:
            return to_persian_digits(str(y))
        if y < 1900 or y > 2100:
            return m.group(0)
        try:
            return to_persian_digits(str(g2j_year(y)))
        except Exception:
            return m.group(0)

    return re.sub(r'(?<!\d)(?:19|20)\d{2}(?!\d)', repl, str(text))


def format_semester_jalali(name: str = '', academic_year: str = '') -> str:
    """نمایش نام ترم + سال تحصیلی به شمسی، مثل: ترم جاری ۱۴۰۵ — ۱۴۰۵-۱۴۰۶"""
    name_j = gregorian_years_in_text(name or '')
    year_j = jalali_year_range(academic_year or '')
    if name_j and year_j:
        return f'{name_j} — {year_j}'
    return name_j or year_j or ''
