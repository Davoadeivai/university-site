from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Enrollment


@receiver(pre_save, sender=Enrollment)
def enrollment_cache_old_status(sender, instance, **kwargs):
    instance._old_status = None
    if not instance.pk:
        return
    try:
        instance._old_status = (
            Enrollment.objects.filter(pk=instance.pk)
            .values_list('status', flat=True)
            .get()
        )
    except Enrollment.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=Enrollment)
def enrollment_sms_notify(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    from core.notify import notify_enrollment_created, notify_enrollment_status

    if created:
        notify_enrollment_created(instance)
        return

    old = getattr(instance, '_old_status', None)
    if old is not None and old != instance.status:
        notify_enrollment_status(instance)
