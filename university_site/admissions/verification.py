"""کد اصالت کارنامهٔ پذیرش.

هر کارنامه یک «کد اصالت» کوتاه دارد که از روی شناسهٔ پرونده و SECRET_KEY
ساخته می‌شود. هر کسی (کارفرما، اداره، دانشگاه دیگر) می‌تواند آن را در صفحهٔ
استعلام عمومی وارد کند و ببیند کارنامه جعلی است یا نه — بدون اینکه هیچ
اطلاعات هویتی افشا شود.

کد قابل حدس نیست چون به SECRET_KEY گره خورده، و قابل ساخت آفلاین است
چون تابع خالص است (نیازی به ذخیرهٔ ستون جدید نیست).
"""
from __future__ import annotations

import hashlib
import hmac

from django.conf import settings

# بدون حروف مبهم I/O/0/1 تا خواندن از روی کاغذ خطا ندهد
_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
_LENGTH = 10


def _digest(tracking_code: str, national_id: str) -> bytes:
    msg = f'{tracking_code}|{national_id}'.encode()
    key = (settings.SECRET_KEY or '').encode()
    return hmac.new(key, msg, hashlib.sha256).digest()


def make_verification_code(application) -> str:
    """کد اصالت ۱۰ کاراکتری به شکل XXXXX-XXXXX."""
    raw = _digest(
        (application.tracking_code or '').strip(),
        (application.national_id or '').strip(),
    )
    n = int.from_bytes(raw[:8], 'big')
    out = []
    for _ in range(_LENGTH):
        out.append(_ALPHABET[n % len(_ALPHABET)])
        n //= len(_ALPHABET)
    code = ''.join(out)
    return f'{code[:5]}-{code[5:]}'


def normalize_code(raw: str) -> str:
    """پاک‌سازی ورودی کاربر: حروف بزرگ، حذف خط تیره و فاصله."""
    s = (raw or '').upper()
    for ch in (' ', '-', '_', '‌', '‏', '‎', '\xa0'):
        s = s.replace(ch, '')
    return s


def check_verification_code(application, raw: str) -> bool:
    """مقایسهٔ زمان‌ثابت تا کد با آزمون‌وخطا کشف نشود."""
    expected = normalize_code(make_verification_code(application))
    given = normalize_code(raw)
    if not given:
        return False
    return hmac.compare_digest(expected, given)


def find_by_code(raw: str):
    """پرونده‌ای که این کد اصالت به آن تعلق دارد (یا None).

    کد به تنهایی معنا ندارد، پس روی پرونده‌های پذیرفته‌شده پیمایش می‌کنیم.
    برای حجم فعلی (چند هزار رکورد) کافی است؛ اگر بزرگ شد باید ستون ایندکس‌شده
    اضافه شود.
    """
    from .models import Application

    given = normalize_code(raw)
    if len(given) != _LENGTH:
        return None
    qs = Application.objects.filter(status='accepted').only(
        'id', 'tracking_code', 'national_id', 'first_name', 'last_name',
        'degree', 'desired_major', 'created_at', 'status',
    ).select_related('desired_major')
    for app in qs.iterator(chunk_size=500):
        if hmac.compare_digest(normalize_code(make_verification_code(app)), given):
            return app
    return None
