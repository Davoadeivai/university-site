"""«دکتر» را پیش از نام معاونان و مدیران گروه می‌گذارد.

    python manage.py prefix_doctor_titles
    python manage.py prefix_doctor_titles --dry-run

سند اصلاحات موسسه: «در عنوان همه مدیران گروه‌ها و معاونت، دکتر قید
گردد».

نامی که از قبل «دکتر» یا عنوان دیگری (مهندس، حجت‌الاسلام، سید…)
دارد دست‌نخورده می‌ماند — دو بار «دکتر دکتر» بدتر از نبودنش است. و
چون بی‌خطر و تکرارپذیر است، در هر دیپلوی اجرا می‌شود.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

# عنوان‌هایی که اگر باشند، «دکتر» اضافه نمی‌شود
EXISTING_TITLES = (
    'دکتر', 'دکتر‌', 'مهندس', 'استاد', 'حجت', 'آیت',
    'پروفسور', 'سرکار', 'جناب',
)


def needs_prefix(name: str) -> bool:
    name = (name or '').strip()
    if not name:
        return False
    return not any(name.startswith(title) for title in EXISTING_TITLES)


class Command(BaseCommand):
    help = 'افزودن «دکتر» به نام معاونان و مدیران گروه'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='فقط گزارش بده، چیزی ذخیره نکن')

    def handle(self, *args, **options):
        from academics.models import AcademicGroup
        from core.models import VicePresidency

        dry = options['dry_run']
        touched = 0

        # ── معاونان ──
        for vice in VicePresidency.objects.all():
            if needs_prefix(vice.full_name):
                new = 'دکتر %s' % vice.full_name.strip()
                self.stdout.write('  معاونت: %s ← %s' % (vice.full_name, new))
                if not dry:
                    vice.full_name = new
                    vice.save(update_fields=['full_name'])
                touched += 1

        # ── مدیران گروه ──
        for group in AcademicGroup.objects.all():
            if not needs_prefix(group.head):
                continue
            new = 'دکتر %s' % group.head.strip()
            self.stdout.write('  گروه %s: %s ← %s'
                              % (group.name, group.head, new))
            if not dry:
                group.head = new
                group.save(update_fields=['head'])
            touched += 1

        if not touched:
            self.stdout.write('همهٔ نام‌ها از قبل عنوان دارند.')
            return

        self.stdout.write(self.style.SUCCESS(
            '%d نام %s' % (touched, 'بررسی شد (بدون ذخیره)' if dry else 'به‌روز شد')))
