"""ارسال پیامک و محدودیت نرخ OTP — مشترک پذیرش و بازیابی رمز."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('django')

OTP_SEND_COOLDOWN = getattr(settings, 'OTP_SEND_COOLDOWN', 60)
OTP_MAX_SEND_PER_HOUR = getattr(settings, 'OTP_MAX_SEND_PER_HOUR', 5)
OTP_MAX_VERIFY_ATTEMPTS = getattr(settings, 'OTP_MAX_VERIFY_ATTEMPTS', 5)


def _send_key(scope: str, phone: str) -> str:
    return f'otp:send:{scope}:{phone}'


def _hour_key(scope: str, phone: str) -> str:
    return f'otp:hour:{scope}:{phone}'


def _verify_key(scope: str, phone: str) -> str:
    return f'otp:verify:{scope}:{phone}'


def can_send_otp(phone: str, scope: str = 'default') -> tuple[bool, str]:
    """آیا ارسال OTP مجاز است؟"""
    if cache.get(_send_key(scope, phone)):
        return False, f'لطفاً {OTP_SEND_COOLDOWN} ثانیه صبر کنید و دوباره تلاش کنید.'
    hour_count = cache.get(_hour_key(scope, phone), 0)
    if hour_count >= OTP_MAX_SEND_PER_HOUR:
        return False, 'تعداد درخواست کد بیش از حد مجاز است. یک ساعت دیگر تلاش کنید.'
    return True, ''


def mark_otp_sent(phone: str, scope: str = 'default') -> None:
    cache.set(_send_key(scope, phone), 1, timeout=OTP_SEND_COOLDOWN)
    hour_key = _hour_key(scope, phone)
    count = cache.get(hour_key, 0) + 1
    cache.set(hour_key, count, timeout=3600)
    cache.delete(_verify_key(scope, phone))


def can_verify_otp(phone: str, scope: str = 'default') -> tuple[bool, str]:
    attempts = cache.get(_verify_key(scope, phone), 0)
    if attempts >= OTP_MAX_VERIFY_ATTEMPTS:
        return False, 'تعداد تلاش‌های ناموفق بیش از حد است. دوباره کد جدید دریافت کنید.'
    return True, ''


def mark_otp_verify_failed(phone: str, scope: str = 'default') -> None:
    key = _verify_key(scope, phone)
    cache.set(key, cache.get(key, 0) + 1, timeout=600)


def clear_otp_verify_attempts(phone: str, scope: str = 'default') -> None:
    cache.delete(_verify_key(scope, phone))


def get_client_ip(request) -> str:
    """آدرس IP کلاینت با در نظر گرفتن پراکسی (X-Forwarded-For)."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def check_rate_limit(request, scope: str, limit: int = 10, window: int = 300,
                     identity: str = '', ip_limit: int | None = None
                     ) -> tuple[bool, str]:
    """محدودیت نرخ برای مسیرهای عمومی (بدون احراز هویت).

    چرا فقط IP کافی نیست
    ────────────────────
    نسخهٔ قبلی تنها روی IP می‌شمرد. اپراتورهای موبایل ایران صدها تا
    هزاران مشترک را پشت یک IP عمومی می‌گذارند (CGNAT)، پس سقف «۵ در
    ۵ دقیقه» یعنی نفر ششمِ همان اپراتور قفل می‌شد — بدون آنکه کاری
    کرده باشد. کاربر VPN روشن می‌کرد، IP عوض می‌شد و ناگهان کار
    می‌کرد؛ از بیرون به‌نظر می‌رسید سایت بدون VPN بالا نمی‌آید.

    راه درست: شمردن روی همان چیزی که باید محافظت شود — شمارهٔ موبایل
    یا کد ملی. کسی که یک شماره را بمباران می‌کند با `identity` گرفته
    می‌شود، و همسایه‌اش روی همان IP آزاد می‌ماند.

    IP همچنان شمرده می‌شود ولی وقتی هویت داریم، سقفش چند برابر است —
    فقط برای جلوی سیل‌آسا گرفتن، نه محدود کردن کاربر عادی. ضریب با
    RATE_LIMIT_IP_MULTIPLIER تنظیم می‌شود.

    برای اندپوینت‌هایی که اصلاً هویتی ندارند (مثل جست‌وجوی زنده)،
    سقف IP همان `limit` است مگر `ip_limit` صریح داده شود. ضریب
    خودکار برایشان اعمال نمی‌شود، چون آنجا IP تنها کلید موجود است و
    بازکردن بی‌دلیلش یعنی برداشتن تنها سپر.

    با RATE_LIMIT_ENABLED=False کل مکانیزم خاموش می‌شود.
    """
    if not getattr(settings, 'RATE_LIMIT_ENABLED', True):
        return True, ''

    minutes = max(1, window // 60)
    too_many = (
        'تعداد درخواست‌ها بیش از حد مجاز است. لطفاً %d دقیقه دیگر '
        'تلاش کنید.' % minutes
    )

    # ۱) سقف دقیق روی هویت — این همان چیزی است که واقعاً باید محدود شود
    if identity:
        key = 'rl:%s:id:%s' % (scope, identity)
        count = cache.get(key, 0)
        if count >= limit:
            return False, too_many
        cache.set(key, count + 1, timeout=window)

    # ۲) سقف IP — سپر در برابر سیل
    if ip_limit is None:
        multiplier = getattr(settings, 'RATE_LIMIT_IP_MULTIPLIER', 20)
        ip_limit = limit * multiplier if identity else limit

    ip = get_client_ip(request)
    ip_key = 'rl:%s:ip:%s' % (scope, ip)
    ip_count = cache.get(ip_key, 0)
    if ip_count >= ip_limit:
        return False, too_many
    cache.set(ip_key, ip_count + 1, timeout=window)

    return True, ''


def _mask(phone: str) -> str:
    """پنهان‌سازی شماره برای لاگ‌ها."""
    if len(phone) >= 6:
        return f'{phone[:4]}****{phone[-2:]}'
    return '****'


def normalize_phone(phone: str) -> str:
    """نرمال‌سازی شماره موبایل ایران به فرمت 09xxxxxxxxx."""
    if not phone:
        return ''
    trans = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
    phone = phone.translate(trans)
    phone = ''.join(ch for ch in phone if ch.isdigit())
    if phone.startswith('98') and len(phone) == 12:
        phone = '0' + phone[2:]
    elif phone.startswith('0098') and len(phone) == 14:
        phone = '0' + phone[4:]
    return phone


def send_sms(phone: str, message: str) -> bool:
    """
    ارسال پیامک متنی از طریق کاوه‌نگار (متد sms_send؛ نیازمند خط ارسال).
    همان الگوی نمونهٔ پنل:
        api = KavenegarAPI(api_key)
        api.sms_send({'sender': ..., 'receptor': ..., 'message': ...})
    """
    phone = normalize_phone(phone)
    sms_enabled = getattr(settings, 'SMS_ENABLED', False)
    api_key = (getattr(settings, 'KAVENEGAR_API_KEY', '') or '').strip()

    if sms_enabled and api_key:
        try:
            from core.kavenegar_client import kavenegar_sms_send
            kavenegar_sms_send(receptor=phone, message=message)
            return True
        except Exception:
            logger.exception('SMS send failed for %s', _mask(phone))
            return False

    # محیط توسعه
    if settings.DEBUG:
        logger.info('[SMS-DEV] → %s | %s', phone, message)
    else:
        logger.warning('SMS disabled; message not delivered to %s', _mask(phone))
    return not sms_enabled  # در dev موفقیت ساختگی برای ادامه فلو


def send_otp(phone: str, code: str, message: str | None = None) -> bool:
    """
    ارسال کد یک‌بارمصرف (OTP).

    اگر KAVENEGAR_OTP_TEMPLATE تنظیم شده باشد از متد verify_lookup کاوه‌نگار
    استفاده می‌کند (بدون نیاز به خط اختصاصی، تحویل سریع‌تر و مطمئن‌تر برای OTP).
    در غیر این صورت به پیامک متنی معمولی (send_sms) برمی‌گردد — مثل نمونه پنل:
    sender + receptor + message.
    """
    phone = normalize_phone(phone)
    sms_enabled = getattr(settings, 'SMS_ENABLED', False)
    api_key = (getattr(settings, 'KAVENEGAR_API_KEY', '') or '').strip()
    template = (getattr(settings, 'KAVENEGAR_OTP_TEMPLATE', '') or '').strip()

    if sms_enabled and api_key and template:
        try:
            from core.kavenegar_client import kavenegar_verify_lookup
            kavenegar_verify_lookup(receptor=phone, token=code, template=template)
            return True
        except Exception:
            logger.exception('OTP verify_lookup failed for %s', _mask(phone))
            return False

    # بدون الگو یا در حالت پیامک متنی: از send_sms استفاده کن
    if message is None:
        message = f'کد تأیید شما: {code}'
    return send_sms(phone, message)
