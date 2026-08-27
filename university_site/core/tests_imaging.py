"""کوچک‌کردن تصویرها — چیزی که صفحه را روی خط کند باز نگه می‌داشت."""
import io
import random
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from core.imaging import shrink
from core.models import Slider

MEDIA = tempfile.mkdtemp(prefix='shrink-test-')


def _save_raw(row):
    """ذخیره بدون گذر از mixin — وضعیت پیش از این اصلاح.

    ‎super(Slider, row).save()‎ به این کار نمی‌آید: در ترتیب ارث‌بری،
    درست پس از Slider خودِ mixin است، نه Model. آن نسخه mixin را
    صدا می‌زد، عکس کوچک می‌شد، و سه آزمون این کلاس بی‌آنکه چیزی را
    بسنجند سبز می‌ماندند.
    """
    from django.db import models

    models.Model.save(row)


def photo(width=4000, height=2600, quality=98, mode='RGB'):
    """عکسی پرجزئیات، تا فشرده‌سازی واقعاً کاری داشته باشد.

    عکس یک‌دست (مثلاً همه سفید) در JPEG چند کیلوبایت می‌شود و
    آزمون را بی‌معنا می‌کند.
    """
    from PIL import Image

    image = Image.new(mode, (width, height))
    pixels = image.load()
    random.seed(7)
    step = 2
    for y in range(0, height, step):
        for x in range(0, width, step):
            value = (random.randint(0, 255), random.randint(0, 255),
                     random.randint(0, 255))
            pixels[x, y] = value + ((255,) if mode == 'RGBA' else ())
    buffer = io.BytesIO()
    image.save(buffer, 'PNG' if mode == 'RGBA' else 'JPEG', quality=quality)
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class ShrinkOnUploadTests(TestCase):
    """اسلاید هشت‌مگابایتی، پیش از دیده‌شدن صفحه باید کامل برسد."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def _slider(self, data, name='big.jpg'):
        slider = Slider(title='اسلاید آزمون', order=1, is_active=True)
        slider.image.save(name, ContentFile(data), save=False)
        slider.save()
        return slider

    def test_a_huge_image_shrinks_on_save(self):
        raw = photo()
        slider = self._slider(raw)
        self.assertLess(slider.image.size, len(raw) / 4)

    def test_it_stops_at_the_declared_width(self):
        slider = self._slider(photo())
        self.assertEqual(slider.image.width, 2000)

    def test_the_aspect_ratio_survives(self):
        """۴۰۰۰×۲۶۰۰ باید ۲۰۰۰×۱۳۰۰ شود، نه کشیده."""
        slider = self._slider(photo(4000, 2600))
        self.assertEqual(slider.image.height, 1300)

    def test_an_already_compressed_image_is_left_alone(self):
        """عکسی که هم در سقف جا می‌شود و هم فشرده است، دست‌نخورده."""
        raw = photo(600, 400, quality=70)
        slider = self._slider(raw, 'lean.jpg')
        self.assertEqual(slider.image.size, len(raw))

    def test_a_small_but_bloated_image_is_still_compressed(self):
        """۶۰۰ پیکسل پهنا هم اگر ۳۰۰ کیلوبایت باشد، بادکرده است."""
        raw = photo(600, 400, quality=100)
        slider = self._slider(raw, 'bloated.jpg')
        self.assertLess(slider.image.size, len(raw))
        self.assertEqual(slider.image.width, 600)

    def test_running_twice_does_not_shrink_twice(self):
        """عکسی که یک بار کوچک شده، نباید هر ذخیره کیفیت از دست بدهد."""
        slider = self._slider(photo())
        once = slider.image.size
        slider.save()
        slider.refresh_from_db()
        self.assertEqual(slider.image.size, once)

    def test_transparency_is_not_turned_black(self):
        """JPEG آلفا ندارد؛ تبدیل کورکورانه پس‌زمینه را سیاه می‌کند."""
        from PIL import Image

        slider = self._slider(photo(2600, 1600, mode='RGBA'), 'clear.png')
        slider.image.open('rb')
        self.assertIn(Image.open(slider.image).mode, ('RGBA', 'LA', 'P'))

    def test_an_unreadable_file_does_not_break_the_save(self):
        """آپلود نباید به‌خاطر بهینه‌سازی بشکند."""
        slider = self._slider(b'this is not an image at all', 'broken.jpg')
        self.assertTrue(Slider.objects.filter(pk=slider.pk).exists())

    def test_an_empty_field_is_no_trouble(self):
        self.assertFalse(shrink(None))

    def test_a_vector_is_left_alone(self):
        """SVG برداری است — کوچک کردنش بی‌معناست."""
        slider = Slider(title='برداری', order=2)
        slider.image.save('mark.svg', ContentFile(b'<svg></svg>'), save=False)
        before = slider.image.size
        slider.save()
        self.assertEqual(slider.image.size, before)

    def test_an_animated_format_is_left_alone(self):
        slider = Slider(title='متحرک', order=3)
        slider.image.save('loop.gif', ContentFile(b'GIF89a' + b'\x00' * 400),
                          save=False)
        before = slider.image.size
        slider.save()
        self.assertEqual(slider.image.size, before)

    def test_saving_one_other_field_does_not_touch_the_image(self):
        """ذخیرهٔ عنوان نباید عکس را از دیسک بخواند و دوباره بنویسد."""
        slider = self._slider(photo())
        before = slider.image.name
        slider.title = 'عنوان تازه'
        slider.save(update_fields=['title'])
        slider.refresh_from_db()
        self.assertEqual(slider.image.name, before)


@override_settings(MEDIA_ROOT=MEDIA)
class ShrinkMediaCommandTests(TestCase):
    """آنچه پیش از این آپلود شده، خودش کوچک نمی‌شود."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def _oversized(self):
        """اسلایدی که از راه بهینه‌سازی رد نشده — مثل آنچه روی سرور است."""
        raw = photo()
        slider = Slider(title='قدیمی', order=1, is_active=True)
        slider.image.save('legacy.jpg', ContentFile(raw), save=False)
        _save_raw(slider)
        return slider, len(raw)

    def _run(self, *args):
        from io import StringIO

        out = StringIO()
        call_command('shrink_media', *args, stdout=out)
        return out.getvalue()

    def test_it_shrinks_what_is_already_there(self):
        slider, raw = self._oversized()
        self._run()
        slider.refresh_from_db()
        self.assertLess(slider.image.size, raw / 4)

    def test_it_reports_what_it_saved(self):
        self._oversized()
        self.assertIn('صرفه‌جویی', self._run())

    def test_dry_run_changes_nothing(self):
        slider, raw = self._oversized()
        output = self._run('--dry-run')
        slider.refresh_from_db()
        self.assertEqual(slider.image.size, raw)
        self.assertIn('dry-run', output)

    def test_running_twice_is_safe(self):
        slider, _ = self._oversized()
        self._run()
        slider.refresh_from_db()
        once = slider.image.size
        self._run()
        slider.refresh_from_db()
        self.assertEqual(slider.image.size, once)

    def test_a_missing_file_does_not_stop_the_sweep(self):
        """بعد از انتقال مدیا، ردیف هست و فایلش نیست."""
        Slider.objects.create(
            title='گمشده', order=2, image='sliders/gone.jpg')
        self.assertIn('پیدا نشد', self._run())

    def test_files_below_the_threshold_are_not_touched(self):
        raw = photo(600, 400, quality=70)
        slider = Slider(title='کوچک', order=3)
        slider.image.save('tiny.jpg', ContentFile(raw), save=False)
        _save_raw(slider)
        self._run()
        slider.refresh_from_db()
        self.assertEqual(slider.image.size, len(raw))


class SlidePriorityTests(TestCase):
    """اسلاید اول تنها تصویری است که پیش از دیده‌شدن صفحه لازم است."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        for index in range(3):
            Slider.objects.create(
                title='اسلاید %d' % index, order=index, is_active=True,
                image='sliders/s%d.jpg' % index)

    def _slides(self):
        from django.urls import reverse

        html = self.client.get(reverse('core:home')).content.decode()
        block = html.split('id="heroTrack"')[1].split('/track')[0]
        return [chunk.split('>')[0]
                for chunk in block.split('<img class="slide-bg"')[1:]]

    def test_only_the_first_slide_loads_eagerly(self):
        slides = self._slides()
        self.assertIn('loading="eager"', slides[0])
        for later in slides[1:]:
            self.assertIn('loading="lazy"', later)

    def test_the_first_slide_goes_to_the_front_of_the_queue(self):
        self.assertIn('fetchpriority="high"', self._slides()[0])

    def test_the_others_are_pushed_back(self):
        for later in self._slides()[1:]:
            self.assertIn('fetchpriority="low"', later)

    def test_decoding_does_not_block_the_page(self):
        for slide in self._slides():
            self.assertIn('decoding="async"', slide)
