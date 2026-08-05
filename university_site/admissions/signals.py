from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Application


@receiver(pre_save, sender=Application)
def application_cache_old_status(sender, instance, **kwargs):
    instance._old_status = None
    if not instance.pk:
        return
    try:
        instance._old_status = (
            Application.objects.filter(pk=instance.pk)
            .values_list('status', flat=True)
            .get()
        )
    except Application.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=Application)
def application_sms_notify(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return

    old = getattr(instance, '_old_status', None)
    status_changed = old is not None and old != instance.status
    if not created and not status_changed:
        return

    def _send():
        # #15: خطاهای notify نباید کل ذخیره را خراب کنند
        try:
            from core.notify import (
                notify_application_created, notify_application_status,
            )
            if created:
                notify_application_created(instance)
            else:
                notify_application_status(instance)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                'application_sms_notify failed for pk=%s', instance.pk)

    # پس از commit، نه داخل تراکنش: اگر تراکنش برگردد، متقاضی نباید
    # پیامک «ثبت شد» گرفته باشد بدون اینکه رکوردی وجود داشته باشد.
    from django.db import transaction
    transaction.on_commit(_send)
