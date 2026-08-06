"""تست‌های بانک اطلاعات موسسه.

تمرکز روی سه چیزی که واقعاً می‌شکنند: بی‌خطر بودن اجرای دوبارهٔ
seed، درست شکستن نام فایل سرفصل‌ها، و اینکه صفحه‌های عمومی با
دادهٔ خالی هم ۲۰۰ برگردانند.
"""
import shutil
import tempfile
from io import StringIO

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import BoardMember
from directory.management.commands.import_curricula import (
    guess_level, parse_name,
)
from directory.models import CurriculumDocument, DirectoryPerson, ExternalResource


class MediaIsolatedTestCase(TestCase):
    """هر تستی که فایل می‌نویسد باید در پوشهٔ موقت بنویسد.

    بدون این، اجرای `manage.py test` روی سرور عکس‌ها و PDFهای تستی را
    داخل media واقعی می‌ریخت و آنجا می‌ماندند.
    """

    @classmethod
    def setUpClass(cls):
        cls._media = tempfile.mkdtemp(prefix='dir-test-')
        cls._override = override_settings(MEDIA_ROOT=cls._media)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._media, ignore_errors=True)


class SeedDirectoryTests(MediaIsolatedTestCase):
    """`seed_directory` باید بارها قابل اجرا باشد بدون ساختن ردیف تکراری."""

    def test_seed_is_idempotent(self):
        out = StringIO()
        call_command('seed_directory', stdout=out)
        first = DirectoryPerson.objects.count()
        self.assertGreater(first, 0, 'seed هیچ ردیفی نساخت')

        call_command('seed_directory', stdout=StringIO())
        self.assertEqual(DirectoryPerson.objects.count(), first,
                         'اجرای دوم ردیف تکراری ساخت')

    def test_seed_fills_every_category(self):
        call_command('seed_directory', stdout=StringIO())
        for key, _label in DirectoryPerson.CATEGORY_CHOICES:
            self.assertTrue(
                DirectoryPerson.objects.filter(category=key).exists(),
                'دستهٔ %s خالی ماند' % key)

    def test_seed_also_fills_the_public_board_pages(self):
        """صفحه‌های «هیات موسس» و «هیات امنا» از core.BoardMember می‌خوانند."""
        call_command('seed_directory', stdout=StringIO())
        self.assertTrue(BoardMember.objects.filter(board_type='founder').exists())
        self.assertTrue(BoardMember.objects.filter(board_type='trustee').exists())

    def test_seed_loads_external_resources(self):
        call_command('seed_directory', stdout=StringIO())
        self.assertTrue(ExternalResource.objects.filter(
            url__startswith='https://').exists())

    def test_photos_are_attached_once_and_not_duplicated(self):
        """اجرای دوباره نباید کپی تازه‌ای از عکس روی دیسک بسازد.

        FileField نام تکراری را با پسوند عددی ذخیره می‌کند، پس بدون
        شرط «فقط اگر عکس ندارد»، هر اجرای seed یک نسخهٔ دیگر می‌ساخت.
        """
        call_command('seed_directory', stdout=StringIO())
        with_photo = DirectoryPerson.objects.exclude(photo='').exclude(photo=None)
        self.assertTrue(with_photo.exists(), 'هیچ عکسی ضمیمه نشد')
        names = sorted(p.photo.name for p in with_photo)

        call_command('seed_directory', stdout=StringIO())
        after = sorted(
            p.photo.name for p in
            DirectoryPerson.objects.exclude(photo='').exclude(photo=None))
        self.assertEqual(names, after, 'اجرای دوم عکس‌ها را دوباره ذخیره کرد')

    def test_an_admin_uploaded_photo_survives_a_reseed(self):
        call_command('seed_directory', stdout=StringIO())
        person = DirectoryPerson.objects.filter(category='faculty').first()
        person.photo.save('custom.jpg', ContentFile(b'better photo'), save=True)
        chosen = person.photo.name

        call_command('seed_directory', stdout=StringIO())
        person.refresh_from_db()
        self.assertEqual(person.photo.name, chosen)

    def test_prune_deactivates_rows_missing_from_the_document(self):
        call_command('seed_directory', stdout=StringIO())
        ghost = DirectoryPerson.objects.create(
            category='staff', full_name='کسی که دیگر نیست', is_active=True)
        call_command('seed_directory', '--prune', stdout=StringIO())
        ghost.refresh_from_db()
        self.assertFalse(ghost.is_active)


class PersonModelTests(TestCase):

    def test_full_name_is_built_from_the_parts_when_blank(self):
        person = DirectoryPerson.objects.create(
            category='staff', first_name='زهرا', last_name='اسدی')
        self.assertEqual(person.full_name, 'زهرا اسدی')

    def test_display_name_prefixes_the_honorific(self):
        person = DirectoryPerson.objects.create(
            category='faculty', honorific='دکتر', full_name='حسن فارسیجانی')
        self.assertEqual(person.display_name, 'دکتر حسن فارسیجانی')

    def test_contact_line_prefers_a_direct_number(self):
        direct = DirectoryPerson.objects.create(
            category='staff', full_name='الف', phone='۰۱۱-۳۵۷۵۰۰۸۰', extension='105')
        internal = DirectoryPerson.objects.create(
            category='staff', full_name='ب', extension='115')
        blank = DirectoryPerson.objects.create(category='staff', full_name='ج')
        self.assertEqual(direct.contact_line, '۰۱۱-۳۵۷۵۰۰۸۰')
        self.assertEqual(internal.contact_line, 'داخلی 115')
        self.assertEqual(blank.contact_line, '')


class CurriculumNameParsingTests(TestCase):
    """نام فایل تنها منبع تاریخ تصویب است — اگر بد شکسته شود، تاریخ غلط می‌نشیند."""

    def test_full_date_is_split_off_the_title(self):
        self.assertEqual(parse_name('جامعه شناسی 400.10.15'),
                         ('جامعه شناسی', '۱۴۰۰/۱۰/۱۵'))

    def test_four_digit_year_is_expanded_correctly(self):
        self.assertEqual(parse_name('مکانیک خودرو 1398.05.14'),
                         ('مکانیک خودرو', '۱۳۹۸/۰۵/۱۴'))

    def test_two_digit_year_becomes_a_thirteen_hundred_year(self):
        title, approved = parse_name('کارشناسی ناپیوسته معماری 99.10.23')
        self.assertEqual(approved, '۱۳۹۹/۱۰/۲۳')

    def test_compact_date_without_separators(self):
        self.assertEqual(parse_name('مدیریت بازرگانی -بازاریابی 13951123'),
                         ('مدیریت بازرگانی -بازاریابی', '۱۳۹۵/۱۱/۲۳'))

    def test_bare_year_is_kept_as_the_approval_date(self):
        self.assertEqual(parse_name('روانشناسی 1403'), ('روانشناسی', '۱۴۰۳'))

    def test_three_digit_year_gets_its_leading_one(self):
        self.assertEqual(parse_name('کارشناسی حسابداری جدید404'),
                         ('کارشناسی حسابداری جدید', '۱۴۰۴'))

    def test_a_title_without_a_date_stays_whole(self):
        self.assertEqual(parse_name('الکترونیک عمومی'), ('الکترونیک عمومی', ''))

    def test_dangling_word_saal_is_removed(self):
        self.assertEqual(parse_name('مهندسی معماری سال 1397'),
                         ('مهندسی معماری', '۱۳۹۷'))

    def test_folder_name_decides_the_level(self):
        self.assertEqual(guess_level('کارشناسی ارشد', 'حسابداری'), 'master')
        self.assertEqual(guess_level('کاردانی پیوسته', 'گرافیک'), 'associate_cont')

    def test_level_falls_back_to_the_filename(self):
        self.assertEqual(
            guess_level('سرفصل مصوب رشته ها', 'کارشناسی پیوسته مدیریت دولتی'),
            'bachelor_cont')

    def test_unknown_level_lands_in_other_rather_than_guessing(self):
        self.assertEqual(guess_level('سرفصل مصوب رشته ها', 'الکترونیک عمومی'), 'other')


class PublicPageTests(MediaIsolatedTestCase):
    """هر صفحه باید با دادهٔ خالی هم ۲۰۰ بدهد، نه ۵۰۰."""

    def test_every_page_renders_when_empty(self):
        for name in ('directory:staff', 'directory:people',
                     'directory:curricula', 'directory:resources'):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_pages_render_with_data(self):
        call_command('seed_directory', stdout=StringIO())
        for name in ('directory:staff', 'directory:people', 'directory:resources'):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_staff_search_narrows_the_list(self):
        DirectoryPerson.objects.create(
            category='staff', full_name='حسن فارسیجانی',
            position='رئیس موسسه', extension='115')
        DirectoryPerson.objects.create(
            category='staff', full_name='زهرا اسدی', position='حسابدار')

        body = self.client.get(reverse('directory:staff'), {'q': 'حسابدار'}).content.decode()
        self.assertIn('زهرا اسدی', body)
        self.assertNotIn('حسن فارسیجانی', body)

    def test_staff_search_matches_an_extension(self):
        DirectoryPerson.objects.create(
            category='staff', full_name='حسن فارسیجانی', extension='115')
        body = self.client.get(reverse('directory:staff'), {'q': '115'}).content.decode()
        self.assertIn('حسن فارسیجانی', body)

    def test_only_active_people_are_listed(self):
        DirectoryPerson.objects.create(
            category='staff', full_name='بازنشسته', is_active=False)
        body = self.client.get(reverse('directory:staff')).content.decode()
        self.assertNotIn('بازنشسته', body)


class CurriculumDownloadTests(MediaIsolatedTestCase):

    def setUp(self):
        self.doc = CurriculumDocument.objects.create(
            title='حسابداری', level='master', approved_on='۱۴۰۰/۰۲/۰۵')
        self.doc.file.save('test.pdf', ContentFile(b'%PDF-1.4 test'), save=True)

    def tearDown(self):
        self.doc.file.delete(save=False)

    def test_download_serves_the_file_and_counts_it(self):
        res = self.client.get(
            reverse('directory:curriculum_download', args=[self.doc.pk]))
        self.assertEqual(res.status_code, 200)
        res.close()
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.download_count, 1)

    def test_inactive_document_is_not_downloadable(self):
        CurriculumDocument.objects.filter(pk=self.doc.pk).update(is_active=False)
        res = self.client.get(
            reverse('directory:curriculum_download', args=[self.doc.pk]))
        self.assertEqual(res.status_code, 404)

    def test_file_size_is_recorded_on_save(self):
        self.assertGreater(self.doc.file_size, 0)
        self.assertIn('کیلوبایت', self.doc.size_display)

    def test_level_filter_only_offers_levels_that_have_documents(self):
        """دکمهٔ فیلتری که به صفحهٔ خالی برسد نباید ساخته شود.

        بررسی روی context است نه متن صفحه: نام مقطع‌ها در نوار ناوبری
        هم می‌آید و جست‌وجو در بدنه همیشه پیدایشان می‌کند.
        """
        res = self.client.get(reverse('directory:curricula'))
        options = res.context['level_options']
        self.assertEqual([o['key'] for o in options], ['master'])
        self.assertEqual(options[0]['count'], 1)
