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


# سی‌ویک استان کشور — برای فرم‌های پذیرش و پروفایل
IRAN_PROVINCES = [
    'آذربایجان شرقی', 'آذربایجان غربی', 'اردبیل', 'اصفهان', 'البرز', 'ایلام',
    'بوشهر', 'تهران', 'چهارمحال و بختیاری', 'خراسان جنوبی', 'خراسان رضوی',
    'خراسان شمالی', 'خوزستان', 'زنجان', 'سمنان', 'سیستان و بلوچستان', 'فارس',
    'قزوین', 'قم', 'کردستان', 'کرمان', 'کرمانشاه', 'کهگیلویه و بویراحمد',
    'گلستان', 'گیلان', 'لرستان', 'مازندران', 'مرکزی', 'هرمزگان', 'همدان', 'یزد',
]

ALLOWED_IMAGE_EXT = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # هم‌تراز UI: ۲ مگابایت


def validate_image_upload(f, label: str = 'فایل', required: bool = False) -> str | None:
    if not f:
        return f'{label} الزامی است.' if required else None
    ext = f.name.rsplit('.', 1)[-1].lower() if '.' in getattr(f, 'name', '') else ''
    if ext not in ALLOWED_IMAGE_EXT:
        return f'{label} باید تصویر (JPG/PNG/…) باشد.'
    size = getattr(f, 'size', 0) or 0
    if size > MAX_UPLOAD_BYTES:
        return f'حجم {label} نباید بیش از ۲ مگابایت باشد.'
    return _too_small(f, label)


# کمینهٔ ضلع کوچک تصویر. عکسی که هر ضلعش زیر این باشد، بزرگ که شود
# خوانا نیست و کارشناس پذیرش باید تلفنی دوباره بخواهدش.
MIN_IMAGE_SIDE = 400


def _too_small(f, label: str) -> str | None:
    """ابعاد تصویر را می‌سنجد؛ اگر Pillow نبود بی‌سروصدا رد می‌شود.

    این بررسی عمداً بعد از حجم می‌آید: فایل بزرگ را نباید اول باز
    کرد. و عمداً خطا را می‌بلعد — یک تصویر خراب را همان مرحلهٔ ذخیره
    رد می‌کند و لازم نیست اینجا هم دوباره تشخیص داده شود.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        position = f.tell()
        with Image.open(f) as image:
            width, height = image.size
        f.seek(position)
    except Exception:                                   # noqa: BLE001
        try:
            f.seek(0)
        except Exception:                               # noqa: BLE001
            pass
        return None
    if min(width, height) < MIN_IMAGE_SIDE:
        return (
            f'{label} کم‌کیفیت است ({width}×{height}). '
            f'تصویری با کمینهٔ {MIN_IMAGE_SIDE} پیکسل در هر ضلع بفرستید.'
        )
    return None


def validate_personnel_photo(f, gender: str = '', hijab_confirmed: bool = False, required: bool = True) -> list[str]:
    """اعتبارسنجی عکس پرسنلی + الزام تأیید حجاب کامل برای بانوان."""
    errors = []
    err = validate_image_upload(f, 'عکس پرسنلی', required=required)
    if err:
        errors.append(err)
    if (gender or '') == 'female' and not hijab_confirmed:
        errors.append(
            'برای متقاضیان خانم، تأیید رعایت حجاب کامل اسلامی در عکس پرسنلی الزامی است.'
        )
    return errors
