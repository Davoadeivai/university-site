from django import template

from core.jalali import format_jalali_date, format_jalali_datetime

register = template.Library()


@register.filter
def jalali_date(value, fmt='long'):
    """
    تاریخ شمسی جلالی.
    {{ dt|jalali_date }}         → ۱۴ اردیبهشت ۱۴۰۴
    {{ dt|jalali_date:"short" }} → ۱۴۰۴/۰۲/۱۴
    {{ dt|jalali_date:"day" }} / month / year / full
    """
    return format_jalali_date(value, fmt=fmt or 'long', persian_digits=True)


@register.filter
def jalali_datetime(value, fmt='short'):
    """
    تاریخ و ساعت شمسی.
    {{ dt|jalali_datetime }} → ۱۴۰۴/۰۲/۱۴ - ۱۴:۳۵
    """
    if fmt == 'long':
        # تاریخ بلند + ساعت
        date_part = format_jalali_date(value, 'long', persian_digits=True)
        time_part = format_jalali_datetime(value, persian_digits=True)
        if ' - ' in time_part:
            return f"{date_part} - {time_part.split(' - ', 1)[1]}"
        return date_part
    return format_jalali_datetime(value, persian_digits=True)


@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter."""
    return value.split(delimiter)
