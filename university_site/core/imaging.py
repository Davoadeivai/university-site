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


def _read(field_file, name):
    """محتوای فایل، و اینکه از قبل روی استوریج نشسته یا تازه آپلود شده.

    فرقش سرنوشت‌ساز است: فایل تازه‌آپلودشده را جنگو بعداً — داخل
    ‎Model.save()‎ و در ‎FileField.pre_save‎ — روی دیسک می‌نویسد. اگر
    اینجا ببندیمش، آن نوشتن با «I/O operation on closed file» می‌شکند
    و افزودن اسلاید در پنل خطای ۵۰۰ می‌دهد.

    در خطا None برمی‌گرداند؛ آپلود نباید بشکند.
    """
    committed = getattr(field_file, '_committed', True)
    try:
        field_file.open('rb')
        data = field_file.read()
    except (OSError, ValueError) as exc:
        # فایل روی دیسک نیست — بعد از انتقال مدیا پیش می‌آید
        logger.warning('عکس خوانده نشد (%s): %s', name, exc)
        return None, committed
    finally:
        if committed:
            # پایین‌تر روی همین فایل می‌نویسیم و ویندوز اجازهٔ
            # پاک‌کردن فایلِ باز را نمی‌دهد؛ روی لینوکس هم رها
            # کردنش یعنی نشت توصیف‌گر در حلقه‌های طولانی.
            try:
                field_file.close()
            except Exception:                      # noqa: BLE001
                pass
        else:
            # آپلود تازه: بستن ممنوع، فقط سر جای اول برگردان تا
            # ذخیرهٔ بعدی جنگو بتواند از ابتدا بخواندش.
            try:
                field_file.seek(0)
            except Exception:                      # noqa: BLE001
                pass
    return data, committed


def _write(field_file, name, data, suffix, committed):
    """نتیجه را جای همان فایل می‌نویسد، نه کنارش."""
    from django.core.files.base import ContentFile

    stem_only = name.rsplit('/', 1)[-1]
    stem_only = (stem_only[:stem_only.rfind('.')]
                 if '.' in stem_only else stem_only)

    if not committed:
        # آپلود تازه: هنوز چیزی روی دیسک نیست، پس بازنویسیِ درجا
        # معنا ندارد. همین‌جا نسخهٔ تازه ذخیره می‌شود و جنگو بعداً
        # می‌بیند که فایل نشسته و دوباره نمی‌نویسدش.
        field_file.save(stem_only + suffix, ContentFile(data), save=False)
        return

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
    field_file.name = storage.save(target, ContentFile(data))

    # فایل قبلی اگر پسوندش عوض شده باشد (PNG که JPEG شد) هنوز هست
    if previous != field_file.name and storage.exists(previous):
        storage.delete(previous)


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

    original, committed = _read(field_file, name)
    if original is None:
        return False

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

    _write(field_file, name, shrunk, suffix, committed)
    return True


# نشانی که به‌جای پس‌زمینه گذاشته می‌شود تا بعد شفافش کنیم. رنگی
# انتخاب می‌شود که در خودِ تصویر نباشد، وگرنه بخشی از خودِ نشان هم
# پاک می‌شود.
_SENTINELS = [(255, 0, 255), (0, 255, 0), (255, 255, 0), (0, 255, 255)]


def _unused_colour(image):
    """رنگی که هیچ پیکسلی از این تصویر ندارد."""
    from PIL import Image, ImageChops

    for colour in _SENTINELS:
        flat = Image.new('RGB', image.size, colour)
        red, green, blue = ImageChops.difference(image, flat).split()
        worst = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        # کمینهٔ اختلاف اگر صفر باشد یعنی پیکسلی دقیقاً همین رنگ است
        if worst.getextrema()[0] > 0:
            return colour
    return None


def drop_flat_background(field_file, tolerance: int = 40) -> bool:
    """پس‌زمینهٔ یکدستِ دور تصویر را شفاف می‌کند.

    چرا لازم شد
    ───────────
    نشان‌هایی که از اینترنت برداشته می‌شوند معمولاً JPEG با پس‌زمینهٔ
    سیاه یا سفیدِ توپر هستند، نه PNG شفاف. چنین فایلی در سربرگ به یک
    مربعِ رنگی تبدیل می‌شود و مدیر سایت راهی برای درست‌کردنش ندارد جز
    آنکه با یک ویرایشگر گرافیکی خودش فایل را بسازد.

    چطور کار می‌کند
    ───────────────
    پُرکردنِ سیلابی از چهار گوشه، نه جایگزینیِ سراسریِ رنگ. فرقش
    همه‌چیز است: در نشانِ جمهوری اسلامی، دایرهٔ سیاهِ وسط هم سیاه
    است، و جایگزینیِ سراسری آن را هم سوراخ می‌کرد. سیلاب فقط به
    ناحیه‌ای می‌رسد که از لبه به آن راه باشد.

    دست‌نگه‌داشتن در سه حالت
    ────────────────────────
    - تصویر از قبل شفافیت دارد؛ کاری لازم نیست.
    - چهار گوشه هم‌رنگ نیستند؛ یعنی پس‌زمینهٔ یکدستی در کار نیست و
      حدس‌زدن خطرناک است.
    - نتیجه تقریباً همه‌چیز را پاک می‌کند یا تقریباً هیچ‌چیز؛ هر دو
      یعنی تشخیص غلط بوده.
    """
    if not field_file:
        return False

    name = getattr(field_file, 'name', '') or ''
    if _extension(name) in UNTOUCHED:
        return False

    try:
        from PIL import Image, ImageChops, ImageDraw, ImageOps
    except ImportError:
        logger.warning('Pillow نصب نیست — پس‌زمینه شفاف نمی‌شود.')
        return False

    original, committed = _read(field_file, name)
    if original is None:
        return False

    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(original)))

        # از قبل شفاف است؟ دست نزن.
        if image.mode in ('RGBA', 'LA') or (
                image.mode == 'P' and 'transparency' in image.info):
            alpha = image.convert('RGBA').getchannel('A')
            if alpha.getextrema()[0] < 250:
                return False

        rgb = image.convert('RGB')
        width, height = rgb.size
        corners = [rgb.getpixel(xy) for xy in
                   ((0, 0), (width - 1, 0), (0, height - 1),
                    (width - 1, height - 1))]
        base = corners[0]
        for corner in corners[1:]:
            if max(abs(a - b) for a, b in zip(base, corner)) > tolerance:
                return False          # پس‌زمینهٔ یکدستی در کار نیست

        sentinel = _unused_colour(rgb)
        if sentinel is None:
            return False

        work = rgb.copy()
        for xy in ((0, 0), (width - 1, 0), (0, height - 1),
                   (width - 1, height - 1)):
            ImageDraw.floodfill(work, xy, sentinel, thresh=tolerance)

        flat = Image.new('RGB', work.size, sentinel)
        red, green, blue = ImageChops.difference(work, flat).split()
        worst = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        # صفر یعنی دقیقاً همان نشان — یعنی پس‌زمینه
        alpha = worst.point(lambda value: 0 if value == 0 else 255)

        cleared = sum(1 for value in alpha.getdata() if value == 0)
        share = cleared / float(max(1, width * height))
        if share < .02 or share > .95:
            return False          # تشخیص غلط بوده

        out = rgb.convert('RGBA')
        out.putalpha(alpha)

        buffer = io.BytesIO()
        out.save(buffer, 'PNG', optimize=True)
        cleaned = buffer.getvalue()
    except Exception as exc:                      # noqa: BLE001
        logger.warning('پس‌زمینه شفاف نشد (%s): %s', name, exc)
        return False

    _write(field_file, name, cleaned, '.png', committed)
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
