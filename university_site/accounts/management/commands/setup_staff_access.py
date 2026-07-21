"""ساخت گروه دسترسی مدیر دانشگاه و همگام‌سازی کاربران موجود."""
from django.core.management.base import BaseCommand

from accounts.models import UserProfile
from accounts.staff_permissions import STAFF_GROUP_NAME, ensure_staff_group, sync_user_role_access


class Command(BaseCommand):
    help = 'ساخت گروه «مدیر دانشگاه» و همگام‌سازی دسترسی کاربران با نقش پروفایل'

    def handle(self, *args, **options):
        group = ensure_staff_group()
        self.stdout.write(self.style.SUCCESS(
            f'گروه «{STAFF_GROUP_NAME}» آماده شد ({group.permissions.count()} مجوز).'
        ))

        staff_count = admin_count = 0
        for profile in UserProfile.objects.select_related('user').all():
            sync_user_role_access(profile.user, profile.role)
            if profile.role == 'staff':
                staff_count += 1
            elif profile.role == 'admin':
                admin_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'همگام‌سازی انجام شد — مدیر دانشگاه: {staff_count} | ادمین: {admin_count}'
        ))
