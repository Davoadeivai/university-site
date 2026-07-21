"""
درگاه پرداخت آنلاین — mock (توسعه) و زرین‌پال (sandbox/production).
"""
from __future__ import annotations

import json
import logging
import uuid
from urllib import error, request

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    pass


def _callback_absolute(request):
    return request.build_absolute_uri(reverse('dashboard:payment_callback'))


def _mock_allowed():
    """درگاه آزمایشی فقط زمانی مجاز است که DEBUG روشن باشد یا صراحتاً اجازه داده شود."""
    return bool(getattr(settings, 'DEBUG', False)) or bool(
        getattr(settings, 'ALLOW_MOCK_PAYMENT', False)
    )


def start_payment(request, payment):
    """
    شروع پرداخت برای یک رکورد dashboard.Payment (pending).
    برمی‌گرداند: dict با keys: redirect_url, authority
    """
    gateway = getattr(settings, 'PAYMENT_GATEWAY', 'mock') or 'mock'

    if gateway != 'zarinpal' and not _mock_allowed():
        raise PaymentGatewayError(
            'درگاه پرداخت به‌درستی پیکربندی نشده است. لطفاً با پشتیبانی تماس بگیرید.'
        )

    payment.gateway = gateway
    payment.save(update_fields=['gateway'])

    if gateway == 'zarinpal':
        return _zarinpal_request(request, payment)
    return _mock_request(request, payment)


def verify_payment(request, payment, authority=None):
    """تأیید پرداخت؛ در صورت موفقیت payment را paid می‌کند."""
    gateway = payment.gateway or getattr(settings, 'PAYMENT_GATEWAY', 'mock')
    authority = authority or payment.authority or request.GET.get('Authority', '')

    if gateway == 'zarinpal':
        return _zarinpal_verify(payment, authority)
    if not _mock_allowed():
        raise PaymentGatewayError('درگاه آزمایشی در محیط عملیاتی غیرفعال است.')
    return _mock_verify(request, payment, authority)


def _mock_request(request, payment):
    authority = f'MOCK-{uuid.uuid4().hex[:16].upper()}'
    payment.authority = authority
    payment.save(update_fields=['authority'])
    url = request.build_absolute_uri(
        reverse('dashboard:payment_mock', args=[payment.pk])
    ) + f'?Authority={authority}'
    return {'redirect_url': url, 'authority': authority}


def _mock_verify(request, payment, authority):
    # در حالت mock فقط با Status=OK و authority منطبق پرداخت می‌شود
    status = request.GET.get('Status', '')
    if status != 'OK' or not authority or authority != payment.authority:
        payment.status = 'failed'
        payment.save(update_fields=['status'])
        return False
    payment.status = 'paid'
    payment.transaction_id = f'TXN-MOCK-{authority[-8:]}'
    payment.payment_date = timezone.now()
    payment.save(update_fields=['status', 'transaction_id', 'payment_date'])
    return True


def _zarinpal_urls():
    sandbox = getattr(settings, 'ZARINPAL_SANDBOX', True)
    if sandbox:
        return {
            'request': 'https://sandbox.zarinpal.com/pg/v4/payment/request.json',
            'verify': 'https://sandbox.zarinpal.com/pg/v4/payment/verify.json',
            'start': 'https://sandbox.zarinpal.com/pg/StartPay/{authority}',
        }
    return {
        'request': 'https://api.zarinpal.com/pg/v4/payment/request.json',
        'verify': 'https://api.zarinpal.com/pg/v4/payment/verify.json',
        'start': 'https://www.zarinpal.com/pg/StartPay/{authority}',
    }


def _http_json(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = request.Request(
        url, data=data,
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
        method='POST',
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        logger.error('Zarinpal HTTP %s: %s', e.code, body)
        raise PaymentGatewayError(f'خطای درگاه پرداخت ({e.code})') from e
    except error.URLError as e:
        logger.error('Zarinpal network error: %s', e)
        raise PaymentGatewayError('ارتباط با درگاه پرداخت برقرار نشد.') from e


def _zarinpal_request(request, payment):
    merchant = getattr(settings, 'ZARINPAL_MERCHANT_ID', '') or ''
    if not merchant:
        raise PaymentGatewayError('ZARINPAL_MERCHANT_ID در تنظیمات تعریف نشده است.')

    urls = _zarinpal_urls()
    # زرین‌پال مبلغ را به ریال می‌گیرد؛ فیلد ما تومان است
    amount_rial = int(payment.amount) * 10
    payload = {
        'merchant_id': merchant,
        'amount': amount_rial,
        'callback_url': _callback_absolute(request),
        'description': payment.description or f'پرداخت #{payment.pk}',
        'metadata': {
            'payment_id': str(payment.pk),
            'mobile': getattr(request.user, 'username', '')[:20],
        },
    }
    result = _http_json(urls['request'], payload)
    data = (result or {}).get('data') or {}
    errors = (result or {}).get('errors')
    if errors:
        raise PaymentGatewayError(str(errors))
    authority = data.get('authority')
    if not authority:
        raise PaymentGatewayError('authority از درگاه دریافت نشد.')

    payment.authority = authority
    payment.save(update_fields=['authority'])
    return {
        'redirect_url': urls['start'].format(authority=authority),
        'authority': authority,
    }


def _zarinpal_verify(payment, authority):
    merchant = getattr(settings, 'ZARINPAL_MERCHANT_ID', '') or ''
    if not merchant:
        raise PaymentGatewayError('ZARINPAL_MERCHANT_ID تعریف نشده است.')
    if not authority:
        payment.status = 'failed'
        payment.save(update_fields=['status'])
        return False

    urls = _zarinpal_urls()
    amount_rial = int(payment.amount) * 10
    result = _http_json(urls['verify'], {
        'merchant_id': merchant,
        'amount': amount_rial,
        'authority': authority,
    })
    data = (result or {}).get('data') or {}
    code = data.get('code')
    # 100 = موفق، 101 = قبلاً تأیید شده
    if code in (100, 101):
        payment.status = 'paid'
        payment.transaction_id = str(data.get('ref_id') or authority)
        payment.payment_date = timezone.now()
        payment.save(update_fields=['status', 'transaction_id', 'payment_date'])
        return True

    payment.status = 'failed'
    payment.save(update_fields=['status'])
    return False
