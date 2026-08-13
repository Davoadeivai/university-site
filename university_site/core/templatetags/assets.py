"""نشانی فایل ثابت، با نسخه‌ای که خودش از محتوای فایل درمی‌آید.

چرا
───
`base.html` تا امروز نسخه را دستی داشت (`?v=20260807a`). هر بار که
CSS یا JS عوض می‌شد و کسی یادش می‌رفت آن رشته را هم عوض کند،
مرورگرها فایل قدیمی را از کش می‌دادند و تغییر «کار نمی‌کرد» — بدون
هیچ خطایی، که بدترین نوع خرابی است. یک بار سر دکمهٔ رفرش کپچا
دقیقاً همین اتفاق افتاد.

حالا نسخه هش محتوای خود فایل است: عوض شدن فایل یعنی عوض شدن
نشانی، و دست‌نخوردن فایل یعنی کش مرورگر معتبر می‌ماند.

هش یک بار حساب و نگه داشته می‌شود؛ روی هر دیپلوی پروسه ری‌استارت
می‌شود، پس کهنه نمی‌ماند.
"""
from __future__ import annotations

import hashlib

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()

_cache: dict[str, str] = {}


def _digest(path: str) -> str:
    if path in _cache:
        return _cache[path]
    stamp = ''
    found = finders.find(path)
    if found:
        try:
            with open(found, 'rb') as fh:
                stamp = hashlib.sha1(fh.read()).hexdigest()[:8]
        except OSError:
            stamp = ''
    _cache[path] = stamp
    return stamp


@register.simple_tag
def static_v(path: str) -> str:
    """مثل static، ولی با ?v=<هش محتوا> ته نشانی."""
    url = static(path)
    stamp = _digest(path)
    return f'{url}?v={stamp}' if stamp else url
