"""پرونده‌های حساس نباید برای هر رهگذری باز باشند.

پیش از این هر چیزی زیر \u200E/media/\u200E را وب‌سرور مستقیم تحویل می‌داد:
تصویر کارت ملی داوطلب، فیش واریزی دانشجو، مدرک تخفیف شهریه. نام
فایل هم همان نامی می‌ماند که کاربر داده بود، پس حدس‌زدنی بود.
"""
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core import private_media


def _png():
    # کوچک‌ترین PNG معتبر
    return SimpleUploadedFile(
        'کارت ملی احمدی.png',
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00'
        b'\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82',
        content_type='image/png')


class TheListOfPrivateFoldersIsKeptInOnePlaceTests(TestCase):

    def test_the_web_server_hands_every_private_folder_to_django(self):
        """اگر پوشه‌ای در \u200E.htaccess\u200E از قلم بیفتد، همان‌جا باز می‌ماند.

        این تست تنها چیزی است که میان دو فهرست پیوند برقرار می‌کند؛
        یکی در پایتون است و دیگری در پیکربندی وب‌سرور.
        """
        rules = (Path(settings.BASE_DIR) / '.htaccess').read_text(
            encoding='utf-8')
        line = next(l for l in rules.splitlines()
                    if l.startswith('RewriteRule ^media/(')
                    and '[L]' in l and 'public/media' not in l)
        for prefix in private_media.PRIVATE_PREFIXES:
            self.assertIn(prefix.rstrip('/'), line,
                          'پوشهٔ %s به جنگو سپرده نشده' % prefix)

    def test_the_ordinary_media_rule_comes_after_the_private_one(self):
        """ترتیب مهم است: قاعدهٔ عمومی زودتر بیاید، همه را می‌بلعد."""
        rules = (Path(settings.BASE_DIR) / '.htaccess').read_text(
            encoding='utf-8')
        self.assertLess(rules.index('RewriteRule ^media/(admissions/docs'),
                        rules.index('RewriteRule ^media/(.*)$ public/media'))

    def test_a_public_folder_is_not_locked_by_mistake(self):
        """عکس خبر و لوگو باید برای همه باز بماند."""
        for public in ('news/x.jpg', 'site/logo.png', 'sliders/1.jpg',
                       'professors/a.jpg'):
            self.assertFalse(private_media.is_private(public), public)

    def test_every_private_folder_is_recognised(self):
        for prefix in private_media.PRIVATE_PREFIXES:
            self.assertTrue(private_media.is_private(prefix + 'a.pdf'))


class TheNamesAreNotGuessableTests(TestCase):

    def test_the_original_file_name_is_thrown_away(self):
        """\u200Eکارت ملی احمدی.jpg\u200E پیش از باز شدن هم گویاست."""
        name = private_media.private_upload_to('payments')(
            None, 'کارت ملی احمدی.jpg')
        self.assertTrue(name.startswith('payments/'))
        self.assertNotIn('احمدی', name)
        self.assertTrue(name.endswith('.jpg'))

    def test_two_uploads_never_collide(self):
        build = private_media.private_upload_to('requests')
        self.assertNotEqual(build(None, 'a.pdf'), build(None, 'a.pdf'))

    def test_a_double_extension_cannot_smuggle_a_script(self):
        name = private_media.private_upload_to('requests')(
            None, 'رسید.php.jpg')
        self.assertTrue(name.endswith('.jpg'))
        self.assertNotIn('.php', name)


@override_settings(MEDIA_ROOT='/tmp/private-media-tests')
class TheDoorIsShutToStrangersTests(TestCase):

    def setUp(self):
        from dashboard.models import Payment, Semester

        self.owner = User.objects.create_user(
            'daneshjoo', 'd@aab.ac.ir', 'Str0ng!Pass2026')
        self.other = User.objects.create_user(
            'digari', 'o@aab.ac.ir', 'Str0ng!Pass2026')
        self.semester = Semester.objects.create(
            name='۱۴۰۵-۱', semester_type='fall', academic_year='۱۴۰۵-۱۴۰۶',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=100))
        self.payment = Payment.objects.create(
            student=self.owner, semester=self.semester,
            amount=1000000, payment_type='tuition',
            receipt_file=_png())
        self.url = '/media/' + self.payment.receipt_file.name

    def tearDown(self):
        import shutil

        shutil.rmtree('/tmp/private-media-tests', ignore_errors=True)

    def test_a_stranger_gets_nothing(self):
        """و ۴۰۴ می‌گیرد، نه ۴۰۳ — تا نفهمد چه فایلی هست و چه نیست."""
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_another_student_cannot_read_it(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_the_owner_can_read_it(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_staff_can_read_it(self):
        staff = User.objects.create_superuser(
            'modir', 'm@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_it_is_never_cached_or_indexed(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('noindex', response['X-Robots-Tag'])

    def test_a_missing_file_looks_the_same_as_a_forbidden_one(self):
        """وگرنه با تفاوتِ ۴۰۳ و ۴۰۴ می‌شد فهرست پرونده‌ها را ساخت."""
        self.client.force_login(self.other)
        missing = self.client.get('/media/payments/ندارد.jpg').status_code
        forbidden = self.client.get(self.url).status_code
        self.assertEqual(missing, forbidden)
        self.assertEqual(missing, 403)

    def test_the_path_cannot_climb_out_of_media(self):
        """\u200E/media/payments/../../config/settings.py\u200E یعنی کلید محرمانه."""
        staff = User.objects.create_superuser(
            'modir2', 'm2@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(staff)
        for attack in ('/media/payments/../../config/settings.py',
                       '/media/payments/....//....//manage.py'):
            self.assertIn(self.client.get(attack).status_code, (301, 404))

    def test_a_public_media_path_is_not_served_from_here(self):
        """بقیهٔ \u200E/media/\u200E کار وب‌سرور است؛ اینجا چیزی لو نمی‌دهد."""
        self.assertEqual(self.client.get('/media/news/x.jpg').status_code, 404)
