"""تصویرهایی که از قبل آپلود شده‌اند را کوچک می‌کند.

    python manage.py shrink_media --dry-run
    python manage.py shrink_media

چرا لازم شد
───────────
از این پس هر آپلود تازه خودش کوچک می‌شود (ShrinkImagesMixin)، اما
آنچه پیش از این بالا رفته دست‌نخورده است. چهار اسلاید صفحهٔ اصلی
روی سرور ۲۲٫۵ مگابایت‌اند — یکی‌شان هشت مگابایت — و همان‌ها هستند
که صفحه را روی خط کند نگه می‌دارند.

چه می‌کند
─────────
هر مدلی که shrink_images دارد را پیدا می‌کند، ردیف‌هایش را می‌خواند
و هر عکس بزرگ‌تر از سقف را دوباره ذخیره می‌کند. فایل قدیمی روی دیسک
می‌ماند و پاک نمی‌شود؛ اگر چیزی بد از آب درآمد، اصلش هست.

بارها قابل اجراست: عکسی که یک بار کوچک شده، دفعهٔ بعد از سقف
کوچک‌تر است و رد می‌شود.
"""
from __future__ import annotations

from django.apps import apps
from django.core.management.base import BaseCommand

from core.imaging import DEFAULT_QUALITY, shrink


def human(size: int) -> str:
    if size >= 1024 * 1024:
        return '%.1f مگابایت' % (size / 1024 / 1024)
    return '%d کیلوبایت' % (size / 1024)


class Command(BaseCommand):
    help = 'کوچک‌کردن تصویرهای آپلودشده'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='فقط بگو چه می‌شود، چیزی را عوض نکن')
        parser.add_argument('--min-kb', type=int, default=300,
                            help='زیر این حجم دست نزن (پیش‌فرض ۳۰۰ کیلوبایت)')

    def handle(self, *args, **options):
        dry = options['dry_run']
        floor = options['min_kb'] * 1024

        saved = touched = skipped = 0
        for model in apps.get_models():
            limits = getattr(model, 'shrink_images', None)
            if not limits:
                continue

            for row in model.objects.all().iterator():
                for name, limit in limits.items():
                    field = getattr(row, name, None)
                    if not field:
                        continue
                    try:
                        before = field.size
                    except (OSError, ValueError):
                        # فایل روی دیسک نیست — بعد از انتقال مدیا پیش می‌آید
                        skipped += 1
                        continue
                    if before < floor:
                        continue

                    width, quality = limit if isinstance(limit, tuple) else (
                        limit, DEFAULT_QUALITY)
                    if dry:
                        self.stdout.write('  ? %s — %s'
                                          % (field.name, human(before)))
                        touched += 1
                        continue

                    if not shrink(field, width, quality):
                        continue
                    row.save(update_fields=[name])
                    after = field.size
                    saved += before - after
                    touched += 1
                    self.stdout.write('  ↓ %s — %s ← %s'
                                      % (field.name, human(after),
                                         human(before)))

        head = 'اگر اجرا شود:' if dry else 'انجام شد:'
        self.stdout.write(self.style.SUCCESS(head))
        self.stdout.write('  %d تصویر' % touched)
        if not dry:
            self.stdout.write('  %s صرفه‌جویی' % human(saved))
        if skipped:
            self.stdout.write('  %d فایل روی دیسک پیدا نشد' % skipped)
        if dry:
            self.stdout.write('')
            self.stdout.write('(‎--dry-run‎ بود؛ هیچ فایلی عوض نشد.)')
