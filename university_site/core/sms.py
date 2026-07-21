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


def check_rate_limit(request, scope: str, limit: int = 10, window: int = 300) -> tuple[bool, str]:
    """
    محدودیت نرخ ساده مبتنی بر IP برای استعلام‌های عمومی (بدون احراز هویت).
    برمی‌گرداند (مجاز؟, پیام‌خطا).
    """
    ip = get_client_ip(request)
    key = f'rl:{scope}:{ip}'
    count = cache.get(key, 0)
    if count >= limit:
        minutes = max(1, window // 60)
        return False, f'تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً {minutes} دقیقه دیگر تلاش کنید.'
    cache.set(key, count + 1, timeout=window)
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
