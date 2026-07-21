from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Announcement, UserProfile
from .staff_permissions import sync_user_role_access

_PROFILE_WATCH_FIELDS = (
    'phone', 'student_id', 'department', 'national_id',
    'role', 'bio', 'birth_date',
)


@receiver(post_save, sender=UserProfile)
def sync_profile_role_permissions(sender, instance, **kwargs):
    """با تغییر نقش پروفایل، دسترسی ادمین مدیر دانشگاه همگام می‌شود."""
    if instance.user_id:
        sync_user_role_access(instance.user, instance.role)


@receiver(pre_save, sender=UserProfile)
def profile_cache_old_fields(sender, instance, **kwargs):
    instance._old_watch = None
    if not instance.pk:
        return
    try:
        old = UserProfile.objects.filter(pk=instance.pk).values(*_PROFILE_WATCH_FIELDS).get()
        instance._old_watch = old
    except UserProfile.DoesNotExist:
        instance._old_watch = None


@receiver(post_save, sender=UserProfile)
def profile_sms_notify(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    from core.notify import notify_profile_created, notify_profile_updated

    if created:
        if instance.phone:
            notify_profile_created(instance)
        return

    old = getattr(instance, '_old_watch', None)
    if not old:
        return
    changed = [
        field for field in _PROFILE_WATCH_FIELDS
        if str(old.get(field) or '') != str(getattr(instance, field) or '')
    ]
    if changed:
        notify_profile_updated(instance, changed)


@receiver(pre_save, sender=Announcement)
def announcement_cache_old_active(sender, instance, **kwargs):
    instance._old_is_active = None
    if not instance.pk:
        return
    try:
        instance._old_is_active = (
            Announcement.objects.filter(pk=instance.pk)
            .values_list('is_active', flat=True)
            .get()
        )
    except Announcement.DoesNotExist:
        instance._old_is_active = None


@receiver(post_save, sender=Announcement)
def announcement_sms_notify(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    from core.notify import notify_announcement

    if not instance.is_active:
        return

    if created:
        notify_announcement(instance)
        return

    old = getattr(instance, '_old_is_active', None)
    if old is False:
        notify_announcement(instance)
