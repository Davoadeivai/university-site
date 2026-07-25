from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Payment


@receiver(pre_save, sender=Payment)
def payment_cache_old_status(sender, instance, **kwargs):
    instance._old_status = None
    if not instance.pk:
        return
    try:
        instance._old_status = (
            Payment.objects.filter(pk=instance.pk)
            .values_list('status', flat=True)
            .get()
        )
    except Payment.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=Payment)
def payment_sms_notify(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    if instance.payment_type != 'tuition':
        return
    old = getattr(instance, '_old_status', None)
    # #15: old=None (رکورد جدید) نباید به‌عنوان transition به paid تلقی شود
    if old is None:
        return
    if instance.status == 'paid' and old != 'paid':
        try:
            from core.notify import notify_tuition_paid
            notify_tuition_paid(instance)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('payment_sms_notify failed for pk=%s', instance.pk)
