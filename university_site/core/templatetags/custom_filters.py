import jdatetime
from django import template
from datetime import date, datetime

register = template.Library()


# ── Persian month names ──────────────────────────────────────────────────────
PERSIAN_MONTHS = [
    '', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
]

PERSIAN_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')


def _to_persian_digits(value: str) -> str:
    return value.translate(PERSIAN_DIGITS)


def _to_jalali(value):
    """Convert a date/datetime object to jdatetime.date."""
    if isinstance(value, datetime):
        return jdatetime.datetime.fromgregorian(datetime=value).date()
    if isinstance(value, date):
        return jdatetime.date.fromgregorian(date=value)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Filter: jalali_date
# Usage: {{ obj.published_at|jalali_date }}         →  ۱۴ اردیبهشت ۱۴۰۴
#        {{ obj.published_at|jalali_date:"short" }}  →  ۱۴۰۴/۰۲/۱۴
# ─────────────────────────────────────────────────────────────────────────────
@register.filter
def jalali_date(value, fmt='long'):
    """
    Converts a Gregorian date/datetime to Jalali (Shamsi).
    fmt='long'   → ۱۴ اردیبهشت ۱۴۰۴
    fmt='short'  → ۱۴۰۴/۰۲/۱۴
    fmt='day'    → ۱۴
    fmt='month'  → اردیبهشت
    fmt='year'   → ۱۴۰۴
    fmt='full'   → پنج‌شنبه ۱۴ اردیبهشت ۱۴۰۴
    """
    if not value:
        return ''
    j = _to_jalali(value)
    if j is None:
        return value

    if fmt == 'short':
        return _to_persian_digits(f"{j.year:04d}/{j.month:02d}/{j.day:02d}")
    if fmt == 'day':
        return _to_persian_digits(str(j.day))
    if fmt == 'month':
        return PERSIAN_MONTHS[j.month]
    if fmt == 'year':
        return _to_persian_digits(str(j.year))
    if fmt == 'full':
        weekdays = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه', 'یکشنبه']
        wd = weekdays[j.weekday()]
        day  = _to_persian_digits(str(j.day))
        year = _to_persian_digits(str(j.year))
        return f"{wd} {day} {PERSIAN_MONTHS[j.month]} {year}"
    # default: long
    day  = _to_persian_digits(str(j.day))
    year = _to_persian_digits(str(j.year))
    return f"{day} {PERSIAN_MONTHS[j.month]} {year}"


# ─────────────────────────────────────────────────────────────────────────────
# Filter: jalali_datetime
# Usage: {{ obj.created_at|jalali_datetime }}  →  ۱۴ اردیبهشت ۱۴۰۴ - ۱۴:۳۵
# ─────────────────────────────────────────────────────────────────────────────
@register.filter
def jalali_datetime(value):
    if not value:
        return ''
    if isinstance(value, datetime):
        j = jdatetime.datetime.fromgregorian(datetime=value)
        date_str = _to_persian_digits(
            f"{j.year:04d}/{j.month:02d}/{j.day:02d}"
        )
        time_str = _to_persian_digits(f"{j.hour:02d}:{j.minute:02d}")
        return f"{date_str} - {time_str}"
    return jalali_date(value)


# ─────────────────────────────────────────────────────────────────────────────
# Filter: split  (existing, preserved)
# ─────────────────────────────────────────────────────────────────────────────
@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter."""
    return value.split(delimiter)
