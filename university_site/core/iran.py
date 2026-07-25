"""ابزارهای مشترک ایران: ارقام، کد ملی، موبایل، انتخاب‌ها."""
from __future__ import annotations

import re
from typing import Iterable

_PERSIAN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def normalize_digits(value) -> str:
    return (str(value) if value is not None else '').translate(_PERSIAN_DIGITS).strip()


def only_digits(value) -> str:
    return ''.join(ch for ch in normalize_digits(value) if ch.isdigit())


def is_valid_mobile(phone: str) -> bool:
    p = only_digits(phone)
    return len(p) == 11 and p.startswith('09')


def is_valid_national_id(nid: str) -> bool:
    """اعتبارسنجی کد ملی ۱۰ رقمی با رقم کنترل."""
    nid = only_digits(nid)
    if len(nid) != 10 or not nid.isdigit():
        return False
    if nid == nid[0] * 10:
        return False
    s = sum(int(nid[i]) * (10 - i) for i in range(9)) % 11
    check = int(nid[9])
    return check == s if s < 2 else check == 11 - s


def is_valid_email(email: str) -> bool:
    email = (email or '').strip()
    if not email:
        return True
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def choice_value(value: str, choices: Iterable, default: str = '') -> str | None:
    allowed = {c[0] if isinstance(c, (list, tuple)) else c for c in choices}
    if value in allowed:
        return value
    return default if default in allowed or default == '' else None


def parse_gpa(raw) -> tuple[float | None, str | None]:
    text = normalize_digits(raw)
    if not text:
        return None, None
    try:
        val = float(text.replace(',', '.'))
    except (TypeError, ValueError):
        return None, 'معدل باید عدد معتبر باشد.'
    if val < 0 or val > 20:
        return None, 'معدل باید بین ۰ تا ۲۰ باشد.'
    return val, None


ALLOWED_IMAGE_EXT = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # هم‌تراز UI: ۲ مگابایت


def validate_image_upload(f, label: str = 'فایل') -> str | None:
    if not f:
        return None
    ext = f.name.rsplit('.', 1)[-1].lower() if '.' in getattr(f, 'name', '') else ''
    if ext not in ALLOWED_IMAGE_EXT:
        return f'{label} باید تصویر (JPG/PNG/…) باشد.'
    size = getattr(f, 'size', 0) or 0
    if size > MAX_UPLOAD_BYTES:
        return f'حجم {label} نباید بیش از ۲ مگابایت باشد.'
    return None
