"""اسلایدهای صفحهٔ اصلی را از یک پوشهٔ عکس می‌سازد.

    python manage.py import_slides "C:/.../صفحه اول نمایش" --dry-run
    python manage.py import_slides "C:/.../صفحه اول نمایش"

چرا لازم شد
───────────
هفت عکس اسلاید موسسه روی دسکتاپ بودند و فقط چهارتاشان به سرور
رسیده بود. آپلود تک‌تک از پنل، برای هر کدام یک رفت‌وبرگشت است و
عکس‌ها هم بین ۴ تا ۸ مگابایت‌اند.

اینجا هر عکس یک ردیف اسلاید می‌شود و هنگام ذخیره خودش تا ۲۰۰۰
پیکسل کوچک و فشرده می‌شود (ShrinkImagesMixin) — همان چیزی که صفحهٔ
اصلی را از ۲۲ مگابایت به حدود ۲ مگابایت می‌آورد.

ترتیب
─────
بر اساس نام فایل، به‌صورت عددی: ۱، ۲، ۱۰ — نه ۱، ۱۰، ۲. اگر
نام‌ها عدد نباشند، ترتیب الفبایی است.

بارها قابل اجراست
─────────────────
اسلاید با نام فایلِ مبدأ شناخته می‌شود؛ اجرای دوباره روی همان پوشه
ردیف تکراری نمی‌سازد.
"""
from __future__ import annotations

import re
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from core.models import Slider

SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


def sort_key(path: Path):
    """۱۰ باید بعد از ۲ بیاید، نه بینِ ۱ و ۳."""
    digits = re.findall(r'\d+', path.stem)
    return (int(digits[0]) if digits else 10 ** 9, path.stem.lower())


class Command(BaseCommand):
    help = 'ساخت اسلایدهای صفحهٔ اصلی از یک پوشهٔ عکس'

    def add_arguments(self, parser):
        parser.add_argument('folder', help='پوشه‌ای که عکس‌های اسلاید در آن است')
        parser.add_argument('--dry-run', action='store_true',
                            help='فقط بگو چه می‌شود، چیزی را عوض نکن')
        parser.add_argument('--replace', action='store_true',
                            help='اسلایدهای فعلی را اول پاک کن')

    @staticmethod
    def _source_stem(name: str) -> str:
        """نام فایل مبدأ، بدون دنبالهٔ تصادفی جنگو."""
        stem = Path(name).stem
        return re.sub(r'_[A-Za-z0-9]{7}$', '', stem).lower()

    def handle(self, *args, **options):
        folder = Path(options['folder'])
        if not folder.is_dir():
            raise CommandError('پوشه پیدا نشد: %s' % folder)

        images = sorted(
            (p for p in folder.iterdir()
             if p.is_file() and p.suffix.lower() in SUFFIXES),
            key=sort_key)
        if not images:
            raise CommandError('عکسی در این پوشه نیست: %s' % folder)

        dry = options['dry_run']
        self.stdout.write('%d عکس پیدا شد.' % len(images))

        if options['replace'] and not dry:
            removed = Slider.objects.count()
            Slider.objects.all().delete()
            if removed:
                self.stdout.write('  %d اسلاید قبلی پاک شد.' % removed)

        # نام فایل‌هایی که از قبل ساخته شده‌اند، برای جلوگیری از تکرار.
        #
        # جنگو وقتی نامی تکراری باشد هفت نویسهٔ تصادفی ته آن می‌چسباند
        # («۱.jpg» می‌شود «1_a7Bc9dE.jpg»)، و کوچک‌کردن هم پسوند را به
        # ‎.jpg‎ عوض می‌کند. بدون برداشتن آن دنباله، اجرای دوم هیچ‌کدام
        # را نمی‌شناخت و هفت اسلاید تکراری می‌ساخت.
        taken = {self._source_stem(name)
                 for name in Slider.objects.values_list('image', flat=True)
                 if name}

        made = skipped = 0
        saved_bytes = 0
        for order, path in enumerate(images, start=1):
            if self._source_stem(path.name) in taken:
                self.stdout.write('  = %s — از قبل هست' % path.name)
                skipped += 1
                continue

            before = path.stat().st_size
            if dry:
                self.stdout.write('  + %s (%.1f مگابایت)'
                                  % (path.name, before / 1024 / 1024))
                made += 1
                continue

            slider = Slider(title='', order=order, is_active=True)
            slider.image.save(path.name, ContentFile(path.read_bytes()),
                              save=False)
            # ذخیره، عکس را هم کوچک می‌کند
            slider.save()
            after = slider.image.size
            saved_bytes += before - after
            made += 1
            self.stdout.write('  + %s — %.1f ← %.1f مگابایت'
                              % (path.name, after / 1024 / 1024,
                                 before / 1024 / 1024))

        head = 'اگر اجرا شود:' if dry else 'انجام شد:'
        self.stdout.write(self.style.SUCCESS(head))
        self.stdout.write('  %d اسلاید تازه' % made)
        if skipped:
            self.stdout.write('  %d از قبل بود' % skipped)
        if saved_bytes > 0:
            self.stdout.write('  %.1f مگابایت صرفه‌جویی'
                              % (saved_bytes / 1024 / 1024))
        if dry:
            self.stdout.write('')
            self.stdout.write('(‎--dry-run‎ بود؛ دیتابیس دست‌نخورده ماند.)')
        else:
            self.stdout.write('')
            self.stdout.write('عنوان اسلایدها خالی است — روی صفحه هم هیچ')
            self.stdout.write('نوشته‌ای نمایش داده نمی‌شود، طبق خواستهٔ موسسه.')
