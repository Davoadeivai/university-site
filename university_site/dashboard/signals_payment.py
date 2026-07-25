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
    if instance.status == 'paid' and old != 'paid':
        from core.notify import notify_tuition_paid
        notify_tuition_paid(instance)
