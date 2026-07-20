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


def send_sms(phone: str, message: str) -> bool:
    """
    ارسال پیامک واقعی از طریق کاوه‌نگار در صورت فعال بودن SMS_ENABLED.
    در توسعه یا خطا: لاگ بدون افشای کامل کد در production.
    """
    sms_enabled = getattr(settings, 'SMS_ENABLED', False)
    api_key = getattr(settings, 'KAVENEGAR_API_KEY', '') or ''
    sender = getattr(settings, 'SMS_SENDER_NUMBER', '') or ''

    if sms_enabled and api_key:
        try:
            import kavenegar
            kavenegar.KavenegarAPI(api_key).sms_send({
                'sender': sender,
                'receptor': phone,
                'message': message,
            })
            return True
        except Exception:
            logger.exception('SMS send failed for %s****%s', phone[:4], phone[-2:])
            return False

    # محیط توسعه
    if settings.DEBUG:
        logger.info('[SMS-DEV] → %s | %s', phone, message)
    else:
        logger.warning(
            'SMS disabled; message not delivered to %s****%s',
            phone[:4], phone[-2:],
        )
    return not sms_enabled  # در dev موفقیت ساختگی برای ادامه فلو
