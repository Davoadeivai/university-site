from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import News


@receiver(pre_save, sender=News)
def news_cache_old_published(sender, instance, **kwargs):
    instance._old_is_published = None
    if not instance.pk:
        return
    try:
        instance._old_is_published = (
            News.objects.filter(pk=instance.pk)
            .values_list('is_published', flat=True)
            .get()
        )
    except News.DoesNotExist:
        instance._old_is_published = None


@receiver(post_save, sender=News)
def news_sms_notify(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    from core.notify import notify_news_published

    if not instance.is_published:
        return

    if created:
        notify_news_published(instance)
        return

    old = getattr(instance, '_old_is_published', None)
    if old is False:
        notify_news_published(instance)
