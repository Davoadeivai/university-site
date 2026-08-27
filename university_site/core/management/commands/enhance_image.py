"""کیفیت یک عکس را برای نمایش روی سایت بهتر می‌کند.

    python manage.py enhance_image "C:/.../cover.jpg"
    python manage.py enhance_image "C:/.../cover.jpg" --width 2000
    python manage.py enhance_image "C:/.../cover.jpg" --out "C:/.../better.jpg"

چه کاری می‌کند
──────────────
عکسی که با موبایل از صفحهٔ نمایش یا از روی کاغذ گرفته شده، سه
مشکل معمول دارد و این دستور هر سه را هدف می‌گیرد:

۱. الگوی مویر — آن نقطه‌های ریزِ صفحهٔ نمایش. یک محو کردن بسیار
   ملایم آن را می‌شکند، پیش از آنکه تیز کردن، خودِ نقطه‌ها را هم
   تیز کند و بدترشان کند.

۲. نرمی و بی‌جانی — با unsharp mask لبه‌ها برمی‌گردند. شعاع کوچک
   و شدت متوسط، چون شدت بالا دور نوشته‌ها هالهٔ سفید می‌سازد.

۳. کنتراست و رنگِ مرده — کشیدن ملایم کنتراست و اشباع.

بزرگ‌نمایی
──────────
اگر عکس از عرض خواسته‌شده کوچک‌تر باشد، با LANCZOS بزرگ می‌شود.
این جزئیاتی که در فایل نیست را نمی‌سازد — فقط باعث می‌شود لبه‌ها
هنگام بزرگ شدن پله‌پله نشوند.

آنچه از دست این دستور برنمی‌آید
───────────────────────────────
عکسی که از صفحهٔ نمایش گرفته شده هیچ‌وقت به کیفیت فایل اصلی
نمی‌رسد. اگر نسخهٔ اصلی جلد در دسترس است، همان را بگذارید.
"""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'بهبود کیفیت یک عکس برای نمایش روی سایت'

    def add_arguments(self, parser):
        parser.add_argument('path', help='مسیر فایل عکس')
        parser.add_argument('--out', help='مسیر خروجی (پیش‌فرض: کنار اصل)')
        parser.add_argument('--width', type=int, default=1600,
                            help='عرض خروجی به پیکسل (پیش‌فرض ۱۶۰۰)')
        parser.add_argument('--quality', type=int, default=92,
                            help='کیفیت JPEG (پیش‌فرض ۹۲)')
        parser.add_argument('--no-descreen', action='store_true',
                            help='الگوی مویر را نشکن (برای عکس‌های سالم)')

    def handle(self, *args, **options):
        try:
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        except ImportError:
            raise CommandError('Pillow نصب نیست.')

        source = Path(options['path'])
        if not source.is_file():
            raise CommandError('فایل پیدا نشد: %s' % source)

        target = Path(options['out']) if options['out'] else source.with_name(
            source.stem + '-enhanced.jpg')

        image = Image.open(source)
        image = ImageOps.exif_transpose(image)
        before = image.size
        image = image.convert('RGB')

        # ۱) شکستن مویر — پیش از تیز کردن، وگرنه نقطه‌ها هم تیز می‌شوند
        if not options['no_descreen']:
            image = image.filter(ImageFilter.GaussianBlur(radius=0.6))

        # ۲) بزرگ‌نمایی تا عرض خواسته‌شده
        width = options['width']
        if image.width < width:
            ratio = width / float(image.width)
            image = image.resize(
                (width, max(1, int(image.height * ratio))), Image.LANCZOS)
        elif image.width > width:
            ratio = width / float(image.width)
            image = image.resize(
                (width, max(1, int(image.height * ratio))), Image.LANCZOS)

        # ۳) برگرداندن لبه‌ها
        image = image.filter(ImageFilter.UnsharpMask(
            radius=1.6, percent=135, threshold=3))

        # ۴) جان دادن به رنگ و کنتراست — ملایم، نه اغراق‌آمیز
        image = ImageEnhance.Contrast(image).enhance(1.10)
        image = ImageEnhance.Color(image).enhance(1.08)
        image = ImageEnhance.Brightness(image).enhance(1.02)

        image.save(target, 'JPEG', quality=options['quality'],
                   optimize=True, progressive=True, subsampling=0)

        self.stdout.write(self.style.SUCCESS('انجام شد:'))
        self.stdout.write('  ورودی : %dx%d — %.0f کیلوبایت'
                          % (before[0], before[1],
                             source.stat().st_size / 1024))
        self.stdout.write('  خروجی : %dx%d — %.0f کیلوبایت'
                          % (image.width, image.height,
                             target.stat().st_size / 1024))
        self.stdout.write('  فایل  : %s' % target)
        self.stdout.write('')
        self.stdout.write('عکسی که از صفحهٔ نمایش گرفته شده هیچ‌وقت به')
        self.stdout.write('کیفیت فایل اصلی نمی‌رسد؛ اگر نسخهٔ اصلی هست،')
        self.stdout.write('همان بهتر است.')
