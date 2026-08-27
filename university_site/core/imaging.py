"""کوچک‌کردن تصویرهای آپلودشده.

چرا لازم شد
───────────
چهار اسلاید صفحهٔ اصلی روی سرور ۲۲٫۵ مگابایت بودند — یکی‌شان
هشت مگابایت، و همان یکی با loading="eager" بار می‌شود، یعنی پیش از
دیده‌شدن صفحه باید کامل برسد. روی خط کند، این یعنی چهل ثانیه صفحهٔ
سفید؛ و صفحهٔ سفید از دید بازدیدکننده یعنی «سایت بالا نمی‌آید».

عکسی که تمام‌عرض نمایش داده می‌شود، بیش از ۱۹۲۰ پیکسل پهنا به چشم
نمی‌آید: پیکسل‌های اضافه فقط وزن‌اند. بنابراین هنگام ذخیره، عکس تا
سقف تعیین‌شده کوچک می‌شود و دوباره فشرده.

چه چیزهایی دست‌نخورده می‌مانند
──────────────────────────────
- SVG و GIF: اولی برداری است و دومی ممکن است متحرک باشد.
- عکسی که از سقف کوچک‌تر است و حجمش هم معقول است.
- فاویکون و لوگو — سقفشان جداگانه و بزرگ‌تر از نیازشان تعریف شده.
- مدارک پذیرش: کارت ملی و مدرک تحصیلی باید خوانا بمانند، پس سقف
  آن‌ها بلندتر است و کیفیتشان بالاتر.

اگر کوچک‌کردن به هر دلیلی شکست بخورد — فایل خراب، فرمت ناشناخته —
فایل اصلی سر جایش می‌ماند. آپلود نباید به‌خاطر بهینه‌سازی بشکند.
"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

# قالب‌هایی که دست نمی‌خورند
UNTOUCHED = {'.svg', '.gif', '.ico', '.webp'}

# پیش‌فرض: پهنای بیشینه به پیکسل، و کیفیت JPEG
DEFAULT_WIDTH = 1920
DEFAULT_QUALITY = 82

# سقف «بایت به‌ازای هر پیکسل».
#
# این عدد جای یک آستانهٔ ثابتِ حجمی نشسته، چون آستانهٔ ثابت دو چیز
# را خراب می‌کرد: عکس کوچکِ ولی بادکرده را رها می‌کرد، و عکسی که یک
# بار فشرده شده بود هر بار دوباره فشرده می‌شد و ذخیره‌های پیاپی
# کیفیتش را می‌خوردند.
#
# یک JPEG سالم با کیفیت ۸۲ معمولاً ۰٫۱ تا ۰٫۵ بایت بر پیکسل است؛
# بالاتر از ۰٫۶ یعنی فشرده‌نشده. پس از یک بار پردازش، فایل زیر این
# خط می‌افتد و دفعهٔ بعد دست‌نخورده رد می‌شود.
BYTES_PER_PIXEL = 0.6


def _extension(name: str) -> str:
    dot = name.rfind('.')
    return name[dot:].lower() if dot >= 0 else ''


def shrink(field_file, max_width: int = DEFAULT_WIDTH,
           quality: int = DEFAULT_QUALITY) -> bool:
    """عکس یک ImageField را کوچک و دوباره فشرده می‌کند.

    برمی‌گرداند True اگر فایل واقعاً عوض شده باشد. خودش ذخیره
    نمی‌کند؛ فراخوان باید save را صدا بزند.
    """
    if not field_file:
        return False

    name = getattr(field_file, 'name', '') or ''
    if _extension(name) in UNTOUCHED:
        return False

    try:
        from PIL import Image, ImageOps
    except ImportError:
        logger.warning('Pillow نصب نیست — تصویرها کوچک نمی‌شوند.')
        return False

    try:
        field_file.open('rb')
        original = field_file.read()
    except (OSError, ValueError) as exc:
        # فایل روی دیسک نیست — بعد از انتقال مدیا پیش می‌آید
        logger.warning('عکس خوانده نشد (%s): %s', name, exc)
        return False
    finally:
        # بستنِ صریح لازم است: پایین‌تر روی همین فایل می‌نویسیم، و
        # ویندوز اجازهٔ پاک‌کردن فایلِ باز را نمی‌دهد. روی لینوکس هم
        # رها کردنش یعنی نشت توصیف‌گر فایل در حلقه‌های طولانی.
        try:
            field_file.close()
        except Exception:                          # noqa: BLE001
            pass

    try:
        image = Image.open(io.BytesIO(original))
        # چرخش را از EXIF بخوان و در خودِ پیکسل‌ها اعمال کن، چون
        # ذخیرهٔ دوباره آن برچسب را می‌اندازد و عکس کج می‌شود
        image = ImageOps.exif_transpose(image)
        width, height = image.size

        # عکسی که هم در سقف پهنا جا می‌شود و هم از قبل فشرده است،
        # دست‌نخورده می‌ماند — وگرنه هر ذخیره یک نسل کیفیت می‌خورد.
        pixels = max(1, width * height)
        already_lean = len(original) / pixels <= BYTES_PER_PIXEL
        if width <= max_width and already_lean:
            return False

        if width > max_width:
            ratio = max_width / float(width)
            image = image.resize(
                (max_width, max(1, int(height * ratio))), Image.LANCZOS)

        # شفافیت را نگه دار: JPEG آلفا ندارد و پس‌زمینه سیاه می‌شود
        has_alpha = image.mode in ('RGBA', 'LA') or (
            image.mode == 'P' and 'transparency' in image.info)
        if has_alpha:
            image = image.convert('RGBA')
            fmt, params, suffix = 'PNG', {'optimize': True}, '.png'
        else:
            image = image.convert('RGB')
            fmt = 'JPEG'
            params = {'quality': quality, 'optimize': True, 'progressive': True}
            suffix = '.jpg'

        buffer = io.BytesIO()
        image.save(buffer, fmt, **params)
        shrunk = buffer.getvalue()
    except Exception as exc:                      # noqa: BLE001
        # فرمت ناشناخته یا فایل خراب — آپلود نباید بشکند
        logger.warning('عکس کوچک نشد (%s): %s', name, exc)
        return False

    # اگر نتیجه بزرگ‌تر شد، همان اصل بهتر است
    if len(shrunk) >= len(original):
        return False

    from django.core.files.base import ContentFile

    # جای همان فایل نوشته می‌شود، نه کنارش.
    #
    # ‎FieldFile.save‎ همیشه نام تازه می‌گیرد و اگر نام اشغال باشد هفت
    # نویسهٔ تصادفی ته آن می‌چسباند. چون همین‌جا داریم روی فایلِ خودمان
    # می‌نویسیم، آن نام همیشه اشغال است: هر ذخیره یک دنبالهٔ تازه
    # اضافه می‌کرد («1.jpg» → «1_aB3.jpg» → «1_aB3_xY9.jpg») و نسخهٔ
    # قبلی را یتیم روی دیسک جا می‌گذاشت.
    folder = name.rsplit('/', 1)[0] + '/' if '/' in name else ''
    stem = name.rsplit('/', 1)[-1]
    stem = stem[:stem.rfind('.')] if '.' in stem else stem
    target = folder + stem + suffix

    storage = field_file.storage
    previous = field_file.name
    if storage.exists(target):
        storage.delete(target)
    field_file.name = storage.save(target, ContentFile(shrunk))

    # فایل قبلی اگر پسوندش عوض شده باشد (PNG که JPEG شد) هنوز هست
    if previous != field_file.name and storage.exists(previous):
        storage.delete(previous)
    return True


class ShrinkImagesMixin:
    """هر عکس این مدل را هنگام ذخیره کوچک می‌کند.

    مدل با ``shrink_images`` می‌گوید کدام فیلدها و با چه سقفی:

        class Slider(ShrinkImagesMixin, models.Model):
            shrink_images = {'image': 2000}

    سقف عدد است (پهنا به پیکسل) یا زوج (پهنا، کیفیت).
    """

    shrink_images: dict = {}

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        changed = []
        for name, limit in self.shrink_images.items():
            # وقتی save فقط چند فیلد را می‌نویسد، عکسی که در آن
            # فهرست نیست اصلاً ذخیره نمی‌شود؛ دست‌زدن به آن بی‌فایده
            # است و فقط یک خواندن اضافه از دیسک می‌سازد.
            if update_fields is not None and name not in update_fields:
                continue
            width, quality = limit if isinstance(limit, tuple) else (
                limit, DEFAULT_QUALITY)
            if shrink(getattr(self, name, None), width, quality):
                changed.append(name)
        if changed and update_fields is not None:
            kwargs['update_fields'] = list(update_fields) + [
                name for name in changed if name not in update_fields]
        super().save(*args, **kwargs)
