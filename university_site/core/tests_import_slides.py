"""وارد کردن اسلایدها و رزومه از روی دیسک."""
import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from core.models import PresidencyOffice, Slider

MEDIA = tempfile.mkdtemp(prefix='import-test-')


def photo(path: Path, width=2600, height=1600):
    """عکس پرنویز، تا فشرده‌سازی واقعاً کاری داشته باشد.

    effect_noise به‌جای حلقهٔ پیکسل‌به‌پیکسل: همان نتیجه، ولی
    صدها برابر سریع‌تر — حلقه، این آزمون‌ها را به تایم‌اوت می‌برد.
    """
    from PIL import Image

    noise = Image.effect_noise((width, height), 90)
    image = Image.merge('RGB', (noise, noise.rotate(90, expand=False), noise))
    image.save(path, 'JPEG', quality=95)


@override_settings(MEDIA_ROOT=MEDIA)
class ImportSlidesTests(TestCase):
    """هفت عکس روی دسکتاپ بودند و چهارتا به سرور رسیده بود."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix='slides-'))
        for name in ('1.jpg', '2.jpg', '10.jpg'):
            photo(self.folder / name)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def _run(self, *args):
        out = StringIO()
        call_command('import_slides', str(self.folder), *args, stdout=out)
        return out.getvalue()

    def test_every_image_becomes_a_slide(self):
        self._run()
        self.assertEqual(Slider.objects.count(), 3)

    def test_ten_comes_after_two(self):
        """ترتیب الفبایی «۱۰» را بین «۱» و «۲» می‌گذارد."""
        self._run()
        names = [Path(s.image.name).stem.split('_')[0]
                 for s in Slider.objects.order_by('order')]
        self.assertEqual(names[0], '1')
        self.assertEqual(names[1], '2')
        self.assertEqual(names[2], '10')

    def test_the_images_are_shrunk_on_the_way_in(self):
        self._run()
        for slider in Slider.objects.all():
            self.assertLessEqual(slider.image.width, 2000)

    def test_slides_carry_no_text(self):
        """موسسه خواست هیچ نوشته‌ای روی اسلاید نباشد."""
        self._run()
        for slider in Slider.objects.all():
            self.assertEqual(slider.title, '')

    def test_they_are_active(self):
        self._run()
        self.assertEqual(Slider.objects.filter(is_active=True).count(), 3)

    def test_running_twice_makes_no_duplicates(self):
        self._run()
        self._run()
        self.assertEqual(Slider.objects.count(), 3)

    def test_the_second_run_says_they_were_already_there(self):
        self._run()
        self.assertIn('از قبل هست', self._run())

    def test_replace_clears_the_old_ones(self):
        Slider.objects.create(title='قدیمی', order=1, image='sliders/x.jpg')
        self._run('--replace')
        self.assertEqual(Slider.objects.count(), 3)
        self.assertFalse(Slider.objects.filter(title='قدیمی').exists())

    def test_dry_run_writes_nothing(self):
        output = self._run('--dry-run')
        self.assertEqual(Slider.objects.count(), 0)
        self.assertIn('dry-run', output)

    def test_a_missing_folder_is_reported_not_crashed(self):
        with self.assertRaises(CommandError):
            call_command('import_slides', str(self.folder / 'nope'),
                         stdout=StringIO())

    def test_a_folder_without_images_is_reported(self):
        empty = Path(tempfile.mkdtemp(prefix='empty-'))
        try:
            with self.assertRaises(CommandError):
                call_command('import_slides', str(empty), stdout=StringIO())
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_non_images_are_left_out(self):
        (self.folder / 'Thumbs.db').write_bytes(b'x')
        (self.folder / 'notes.txt').write_text('hi', encoding='utf-8')
        self._run()
        self.assertEqual(Slider.objects.count(), 3)


@override_settings(MEDIA_ROOT=MEDIA)
class PresidentCvImportTests(TestCase):
    """رزومه تا امروز باید دستی از پنل آپلود می‌شد."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix='cv-'))
        self.pdf = self.folder / 'CV-Dr Farsijani-1405-.pdf'
        self.pdf.write_bytes(b'%PDF-1.4 fake')

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def _run(self, *args):
        out = StringIO()
        call_command('seed_president_cv', *args, stdout=out)
        return out.getvalue()

    def test_the_file_is_attached(self):
        self._run('--cv', str(self.pdf))
        office = PresidencyOffice.objects.first()
        self.assertTrue(office.president_cv)

    def test_it_gets_a_stable_name(self):
        """نشانی دانلود نباید هر بار عوض شود."""
        self._run('--cv', str(self.pdf))
        office = PresidencyOffice.objects.first()
        self.assertIn('CV-Dr-Farsijani', office.president_cv.name)

    def test_a_missing_file_is_reported_not_fatal(self):
        output = self._run('--cv', str(self.folder / 'nope.pdf'))
        self.assertIn('پیدا نشد', output)

    def test_a_wrong_format_is_refused(self):
        other = self.folder / 'cv.txt'
        other.write_text('x', encoding='utf-8')
        output = self._run('--cv', str(other))
        self.assertIn('PDF یا Word', output)
        office = PresidencyOffice.objects.first()
        self.assertFalse(office.president_cv)

    def test_word_is_accepted(self):
        doc = self.folder / 'cv.docx'
        doc.write_bytes(b'PK fake')
        self._run('--cv', str(doc))
        office = PresidencyOffice.objects.first()
        self.assertTrue(office.president_cv.name.endswith('.docx'))

    def test_without_the_flag_nothing_is_attached(self):
        self._run()
        office = PresidencyOffice.objects.first()
        self.assertFalse(office.president_cv)
