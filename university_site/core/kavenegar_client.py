"""
کلاینت کاوه‌نگار — منطبق با نمونه‌های رسمی:
https://github.com/kavenegar/kavenegar-examples-python

  sms_send.py       → kavenegar_sms_send()
  verify_lookup.py  → kavenegar_verify_lookup()  (OTP)

API Key را فقط در .env بگذار: KAVENEGAR_API_KEY
"""
from __future__ import annotations

from django.conf import settings


def _api_key() -> str:
    api_key = (getattr(settings, 'KAVENEGAR_API_KEY', '') or '').strip()
    if not api_key:
        raise ValueError('KAVENEGAR_API_KEY در .env تنظیم نشده است.')
    if '*' in api_key:
        raise ValueError('API Key ماسک‌شده است. کلید کامل بدون ستاره را در .env بگذارید.')
    return api_key


def _default_sender() -> str:
    return (getattr(settings, 'SMS_SENDER_NUMBER', '') or '').strip() or '2000660110'


def kavenegar_sms_send(receptor: str, message: str, sender: str | None = None):
    """
    معادل رسمی sms_send.py:

        api = KavenegarAPI(api_key)
        params = {'sender': ..., 'receptor': ..., 'message': ...}
        response = api.sms_send(params)
    """
    from kavenegar import KavenegarAPI, APIException, HTTPException

    api = KavenegarAPI(_api_key())
    try:
        params = {
            'sender': sender if sender is not None else _default_sender(),
            'receptor': receptor,
            'message': message,
        }
        return api.sms_send(params)
    except (APIException, HTTPException):
        raise
    finally:
        close = getattr(api, 'close', None)
        if callable(close):
            close()


def kavenegar_verify_lookup(
    receptor: str,
    token: str,
    template: str | None = None,
    token2: str = '',
    token3: str = '',
    type_: str = 'sms',
):
    """
    معادل رسمی verify_lookup.py (ارسال OTP):

        api = KavenegarAPI(api_key)
        params = {
            'receptor': ...,
            'template': ...,
            'token': ...,
            'type': 'sms',
        }
        response = api.verify_lookup(params)
    """
    from kavenegar import KavenegarAPI, APIException, HTTPException

    if template is None:
        template = (getattr(settings, 'KAVENEGAR_OTP_TEMPLATE', '') or '').strip()
    if not template:
        raise ValueError('KAVENEGAR_OTP_TEMPLATE در .env تنظیم نشده است.')

    api = KavenegarAPI(_api_key())
    try:
        params = {
            'receptor': receptor,
            'template': template,
            'token': str(token),
            'type': type_,
        }
        if token2:
            params['token2'] = token2
        if token3:
            params['token3'] = token3
        return api.verify_lookup(params)
    except (APIException, HTTPException):
        raise
    finally:
        close = getattr(api, 'close', None)
        if callable(close):
            close()
