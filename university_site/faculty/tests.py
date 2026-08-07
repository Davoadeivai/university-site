"""تست‌های ساخت پروندهٔ استاد از روی «افراد موسسه».

صفحهٔ عمومی اساتید از `faculty.Professor` می‌خواند، ولی فهرست واقعی
اعضای علمی در `directory.DirectoryPerson` بود — یعنی موسسه ۵۵ عضو
علمی داشت و صفحهٔ اساتیدش خالی بود.
"""
import shutil
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from directory.models import DirectoryPerson
from faculty.management.commands.import_from_directory import split_name
from faculty.models import Professor


class NameSplitTests(TestCase):
    """فارسی قاعدهٔ قطعی ندارد؛ مهم این است که چیزی گم نشود."""

    def test_a_two_part_name_splits_in_the_obvious_place(self):
        self.assertEqual(split_name('فاطمه نمازی'), ('فاطمه', 'نمازی'))

    def test_a_compound_surname_stays_together(self):
        self.assertEqual(split_name('جلال قنبری جلودار'),
                         ('جلال', 'قنبری جلودار'))

    def test_sayyed_is_kept_with_the_given_name(self):
        self.assertEqual(split_name('سیده مریم بابانژاد باقری'),
                         ('سیده مریم', 'بابانژاد باقری'))

    def test_sayyed_alone_with_two_parts_is_not_split_further(self):
        self.assertEqual(split_name('سید احمدی'), ('سید', 'احمدی'))

    def test_nothing_is_dropped_whatever_the_shape(self):
        for name in ('حسن فارسیجانی', 'محمدرضا خسروی مقدم',
                     'سیده طاهره جلالی', 'ندا', 'ام‌البنین قاسمی'):
            with self.subTest(name=name):
                first, last = split_name(name)
                self.assertEqual(('%s %s' % (first, last)).strip(), name)

    def test_an_empty_name_does_not_crash(self):
        self.assertEqual(split_name(''), ('', ''))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='prof-test-'))
class ImportFromDirectoryTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        from django.conf import settings
        shutil.rmtree(str(settings.MEDIA_ROOT), ignore_errors=True)

    def _seed(self):
        call_command('seed_directory', stdout=StringIO())

    def test_every_academic_gets_a_professor_record(self):
        self._seed()
        expected = DirectoryPerson.objects.filter(
            category__in=('faculty', 'group_head', 'lecturer'),
            is_active=True).values_list('full_name', flat=True)
        call_command('import_from_directory', stdout=StringIO())
        self.assertEqual(Professor.objects.count(), len(set(expected)))

    def test_running_twice_does_not_duplicate(self):
        self._seed()
        call_command('import_from_directory', stdout=StringIO())
        first = Professor.objects.count()
        call_command('import_from_directory', stdout=StringIO())
        self.assertEqual(Professor.objects.count(), first)

    def test_someone_in_two_categories_is_recorded_once(self):
        """مدیر گروهی که عضو هیات علمی هم هست نباید دو پرونده بگیرد."""
        self._seed()
        call_command('import_from_directory', stdout=StringIO())
        self.assertEqual(
            Professor.objects.filter(last_name='قنبری جلودار').count(), 1)

    def test_a_doctorate_known_only_from_the_honorific_still_counts(self):
        """رئیس موسسه در جدول مدیران گروه مدرک ندارد، ولی «دکتر» دارد.

        بدون این، روی صفحهٔ اساتید «مربی» ثبت می‌شد.
        """
        self._seed()
        call_command('import_from_directory', stdout=StringIO())
        chief = Professor.objects.get(last_name='فارسیجانی')
        self.assertEqual(chief.rank, 'assistant')

    def test_lecturers_are_marked_part_time(self):
        self._seed()
        call_command('import_from_directory', stdout=StringIO())
        someone = Professor.objects.filter(last_name='آقاجانی').first()
        self.assertIsNotNone(someone)
        self.assertEqual(someone.status, 'part_time')

    def test_photos_carry_over(self):
        self._seed()
        call_command('import_from_directory', stdout=StringIO())
        self.assertTrue(
            Professor.objects.exclude(photo='').exists(), 'هیچ عکسی منتقل نشد')

    def test_draft_mode_keeps_them_off_the_site(self):
        self._seed()
        call_command('import_from_directory', '--draft', stdout=StringIO())
        self.assertFalse(Professor.objects.filter(is_active=True).exists())

    def test_dry_run_writes_nothing(self):
        self._seed()
        call_command('import_from_directory', '--dry-run', stdout=StringIO())
        self.assertEqual(Professor.objects.count(), 0)

    def test_an_edit_made_in_the_admin_is_not_overwritten(self):
        self._seed()
        call_command('import_from_directory', stdout=StringIO())
        person = Professor.objects.get(last_name='فارسیجانی')
        person.specialization = 'متن دستیِ ادمین'
        person.save()

        call_command('import_from_directory', stdout=StringIO())
        person.refresh_from_db()
        self.assertEqual(person.specialization, 'متن دستیِ ادمین')

    def test_the_public_page_stops_being_empty(self):
        self._seed()
        empty = self.client.get(reverse('faculty:list')).content
        call_command('import_from_directory', stdout=StringIO())
        filled = self.client.get(reverse('faculty:list'))
        self.assertEqual(filled.status_code, 200)
        self.assertGreater(len(filled.content), len(empty))
        self.assertIn('فارسیجانی', filled.content.decode())

    def test_skip_lecturers_leaves_only_the_faculty(self):
        self._seed()
        call_command('import_from_directory', '--skip-lecturers',
                     stdout=StringIO())
        self.assertTrue(Professor.objects.exists())
        self.assertFalse(
            Professor.objects.filter(last_name='آقاجانی').exists())
