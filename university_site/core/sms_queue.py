"""صف پیامک — بیرون بردن ارسال از مسیر درخواست کاربر.

مسئله‌ای که حل می‌کند
─────────────────────
تا پیش از این، سیگنال `post_save` روی درخواست پذیرش مستقیماً کاوه‌نگار
را صدا می‌زد. یعنی متقاضی دکمهٔ «ثبت» را می‌زد و تا وقتی سرور پیامک
جواب نمی‌داد، صفحه‌اش نمی‌چرخید. با ۵ worker و ۲ ثانیه تأخیر، سقف
واقعی حدود ۲.۵ ثبت‌نام در ثانیه بود — و اگر کاوه‌نگار کند یا قطع
می‌شد، همهٔ workerها همان‌جا قفل می‌شدند و کل سایت می‌خوابید.

حالا پیام در جدول ثبت می‌شود و درخواست بلافاصله برمی‌گردد. یک cron
هر چند دقیقه صف را خالی می‌کند.

راه‌اندازی روی سرور
───────────────────
۱. در .env بگذارید:  SMS_QUEUE=True
۲. یک Cron Job بسازید (cPanel ← Cron Jobs)، هر ۵ دقیقه:

     cd ~/apps/university_site && python manage.py send_sms_queue

بدون cron، با SMS_QUEUE=True پیام‌ها فقط در صف می‌مانند و ارسال
نمی‌شوند — پس یا cron بسازید یا SMS_QUEUE را False بگذارید.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class QueuedSMS(models.Model):
    """یک پیامک در انتظار ارسال."""

    STATUS_CHOICES = [
        ('pending', _('در صف')),
        ('sent', _('ارسال شد')),
        ('failed', _('ناموفق')),
    ]

    phone = models.CharField(_('شماره موبایل'), max_length=20, db_index=True)
    message = models.TextField(_('متن پیام'))
    status = models.CharField(
        _('وضعیت'), max_length=10, choices=STATUS_CHOICES,
        default='pending', db_index=True,
    )
    attempts = models.PositiveSmallIntegerField(_('تعداد تلاش'), default=0)
    last_error = models.CharField(_('آخرین خطا'), max_length=300, blank=True)
    created_at = models.DateTimeField(_('زمان ثبت'), auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(_('زمان ارسال'), null=True, blank=True)

    class Meta:
        app_label = 'core'
        verbose_name = _('پیامک در صف')
        verbose_name_plural = _('صف پیامک')
        ordering = ['-created_at']

    def __str__(self):
        return '%s — %s' % (self.phone, self.get_status_display())

    @property
    def preview(self) -> str:
        text = (self.message or '').replace('\n', ' ')
        return text[:60] + ('…' if len(text) > 60 else '')


# حداکثر تلاش برای هر پیام؛ بعد از آن «ناموفق» می‌شود تا صف بی‌نهایت
# دور نزند و شمارهٔ اشتباه، هر بار هزینه نسازد.
MAX_ATTEMPTS = 3


def queue_enabled() -> bool:
    return bool(getattr(settings, 'SMS_QUEUE', False))


def enqueue(phone: str, message: str) -> bool:
    """ثبت پیام در صف. اگر صف خاموش باشد False برمی‌گرداند."""
    if not queue_enabled():
        return False
    if not phone or not message:
        return False
    QueuedSMS.objects.create(phone=phone, message=message)
    return True


def flush(limit: int = 50) -> dict:
    """ارسال پیام‌های در صف. برای فراخوانی از cron.

    برمی‌گرداند: {'sent': n, 'failed': n, 'left': n}
    """
    from core.sms import send_sms

    sent = failed = 0
    batch = list(
        QueuedSMS.objects.filter(status='pending')
        .order_by('created_at')[:limit]
    )

    for item in batch:
        item.attempts += 1
        try:
            ok = send_sms(item.phone, item.message)
        except Exception as exc:            # پیامک نباید کل cron را بخواباند
            ok = False
            item.last_error = str(exc)[:300]
            logger.exception('ارسال پیامک صف شکست خورد pk=%s', item.pk)

        if ok:
            item.status = 'sent'
            item.sent_at = timezone.now()
            item.last_error = ''
            sent += 1
        elif item.attempts >= MAX_ATTEMPTS:
            item.status = 'failed'
            failed += 1

        item.save(update_fields=['status', 'attempts', 'last_error', 'sent_at'])

    return {
        'sent': sent,
        'failed': failed,
        'left': QueuedSMS.objects.filter(status='pending').count(),
    }
