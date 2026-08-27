"""بهبود کیفیت عکس، برای عکسی که با موبایل از صفحه گرفته شده."""
import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase


def _screen_photo(path: Path, width=840, height=1200):
    """عکسی با الگوی نقطه‌ای — همان مویری که از صفحهٔ نمایش می‌آید."""
    from PIL import Image

    image = Image.new('RGB', (width, height), (240, 238, 235))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            if y < height // 3:
                pixels[x, y] = (200, 40, 20)
            if x % 3 == 0 and y % 3 == 0:
                r, g, b = pixels[x, y]
                pixels[x, y] = (max(0, r - 25), max(0, g - 25), max(0, b - 25))
    image.save(path, 'JPEG', quality=70)


class EnhanceImageTests(SimpleTestCase):

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix='enhance-'))
        self.source = self.folder / 'cover.jpg'
        _screen_photo(self.source)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def _run(self, *args):
        out = StringIO()
        call_command('enhance_image', str(self.source), *args, stdout=out)
        return out.getvalue()

    def test_it_writes_a_new_file_beside_the_original(self):
        self._run()
        self.assertTrue((self.folder / 'cover-enhanced.jpg').is_file())

    def test_the_original_is_left_untouched(self):
        before = self.source.read_bytes()
        self._run()
        self.assertEqual(self.source.read_bytes(), before)

    def test_it_reaches_the_width_asked_for(self):
        from PIL import Image

        self._run('--width', '1400')
        with Image.open(self.folder / 'cover-enhanced.jpg') as image:
            self.assertEqual(image.width, 1400)

    def test_the_shape_is_not_stretched(self):
        from PIL import Image

        with Image.open(self.source) as original:
            ratio = original.height / original.width
        self._run('--width', '1400')
        with Image.open(self.folder / 'cover-enhanced.jpg') as image:
            self.assertAlmostEqual(image.height / image.width, ratio, places=2)

    def test_a_named_output_is_honoured(self):
        target = self.folder / 'better.jpg'
        self._run('--out', str(target))
        self.assertTrue(target.is_file())

    def test_a_wide_photo_is_brought_down_not_only_up(self):
        from PIL import Image

        self._run('--width', '500')
        with Image.open(self.folder / 'cover-enhanced.jpg') as image:
            self.assertEqual(image.width, 500)

    def test_it_says_what_changed(self):
        output = self._run()
        self.assertIn('ورودی', output)
        self.assertIn('خروجی', output)

    def test_it_is_honest_about_what_it_cannot_do(self):
        """بهبود، جایگزین فایل اصلی نیست."""
        self.assertIn('نسخهٔ اصلی', self._run())

    def test_a_missing_file_is_reported_not_crashed(self):
        with self.assertRaises(CommandError):
            call_command('enhance_image', str(self.folder / 'nope.jpg'),
                         stdout=StringIO())

    def test_descreening_can_be_turned_off(self):
        """عکس سالم لازم نیست اول محو شود."""
        target = self.folder / 'sharp.jpg'
        self._run('--no-descreen', '--out', str(target))
        self.assertTrue(target.is_file())
