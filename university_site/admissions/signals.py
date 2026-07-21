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
    from core.notify import notify_application_created, notify_application_status

    if created:
        notify_application_created(instance)
        return

    old = getattr(instance, '_old_status', None)
    if old is not None and old != instance.status:
        notify_application_status(instance)
