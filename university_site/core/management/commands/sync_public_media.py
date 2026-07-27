"""
همگام‌سازی MEDIA_ROOT واقعی با مسیر سرو عمومی public/media.

روی هاست cPanel مسیر /media/ از public/media سرو می‌شود،
ولی manage.py با settings توسعه ممکن است فایل‌ها را در media/ ذخیره کند.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'کپی فایل‌های media/ به public/media برای سرو روی وب'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        src = base / 'media'
        dest = base / 'public' / 'media'
        dry = options['dry_run']

        if not src.is_dir():
            self.stdout.write(self.style.WARNING(f'منبع نیست: {src}'))
            return

        dest.mkdir(parents=True, exist_ok=True)
        copied = skipped = 0
        for path in src.rglob('*'):
            if not path.is_file():
                continue
            rel = path.relative_to(src)
            target = dest / rel
            if target.exists() and target.stat().st_size == path.stat().st_size:
                skipped += 1
                continue
            if dry:
                self.stdout.write(f'COPY {rel}')
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            copied += 1

        self.stdout.write(self.style.SUCCESS(
            f'همگام‌سازی: {copied} کپی، {skipped} بدون تغییر → {dest}'
        ))
