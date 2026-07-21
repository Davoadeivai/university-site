"""
تست مستقیم نمونهٔ پنل کاوه‌نگار:

    python manage.py shell < core/kavenegar_sample.py
یا:
    python manage.py test_kavenegar 09195221749
"""
from django.conf import settings

from core.kavenegar_client import kavenegar_sms_send

# همان پارامترهای نمونهٔ پنل
SENDER = getattr(settings, 'SMS_SENDER_NUMBER', '') or '2000660110'
RECEPTOR = '09195221749'
MESSAGE = '.وب سرویس پیام کوتاه کاوه نگار'

response = kavenegar_sms_send(
    receptor=RECEPTOR,
    message=MESSAGE,
    sender=SENDER,
)
print(response)
