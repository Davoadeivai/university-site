"""مدیر گروه — یک منبع، چند نما."""
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicGroup, Department
from faculty.models import Professor


class GroupHeadFromFacultyTests(TestCase):
    """نام مدیر گروه نباید کپی دوم یک استاد باشد."""

    def setUp(self):
        cache.clear()
        self.faculty = Department.objects.create(
            name='دانشکده فنی', slug='fanni', is_active=True)
        self.professor = Professor.objects.create(
            first_name='مریم', last_name='رضایی', slug='maryam-rezaee',
            department=self.faculty, rank='associate',
            email='rezaee@aab.ac.ir', phone='02133334444')
        self.group = AcademicGroup.objects.create(
            name='گروه کامپیوتر', slug='computer',
            department=self.faculty, is_active=True)

    def test_linking_a_professor_gives_the_name(self):
        self.group.head_professor = self.professor
        self.group.save(update_fields=['head_professor'])
        self.assertEqual(self.group.head_name, 'مریم رضایی')

    def test_the_rank_comes_along(self):
        """مرتبهٔ علمی چیزی است که کپی متنی هیچ‌وقت نداشت."""
        self.group.head_professor = self.professor
        self.assertEqual(self.group.head_rank, 'دانشیار')

    def test_the_contact_details_come_along(self):
        self.group.head_professor = self.professor
        self.assertEqual(self.group.head_contact_email, 'rezaee@aab.ac.ir')
        self.assertEqual(self.group.head_contact_phone, '02133334444')

    def test_it_links_to_the_professor_page(self):
        self.group.head_professor = self.professor
        self.assertEqual(self.group.head_page,
                         self.professor.get_absolute_url())

    def test_a_manual_name_still_works(self):
        """مدیر گروهی که عضو هیئت علمی نیست باید بشود نوشت."""
        self.group.head = 'دکتر احمدی'
        self.assertEqual(self.group.head_name, 'دکتر احمدی')
        self.assertEqual(self.group.head_rank, '')
        self.assertEqual(self.group.head_page, '')

    def test_the_typed_name_wins_over_the_link(self):
        """کسی که در کادر نامی می‌نویسد، انتظار دارد همان را ببیند.

        پیش از این پروندهٔ استاد مقدم بود و نوشتن در کادر هیچ اثری
        نداشت — مدیر سایت نام را عوض می‌کرد و صفحه تکان نمی‌خورد.
        عکس و مرتبه و راه تماس همچنان از پرونده می‌آیند.
        """
        self.group.head = 'نام تازه'
        self.group.head_professor = self.professor
        self.assertEqual(self.group.head_name, 'نام تازه')
        self.assertEqual(self.group.head_rank,
                         self.professor.get_rank_display())

    def test_nothing_recorded_says_nothing(self):
        self.assertEqual(self.group.head_name, '')
        self.assertIsNone(self.group.head_image)

    def test_renaming_the_professor_updates_the_group(self):
        """همان چیزی که کپی متنی نمی‌توانست: یک جا عوض، همه‌جا تازه."""
        self.group.head_professor = self.professor
        self.group.save(update_fields=['head_professor'])
        self.professor.last_name = 'رضایی‌فر'
        self.professor.save(update_fields=['last_name'])
        self.group.refresh_from_db()
        self.assertEqual(self.group.head_name, 'مریم رضایی‌فر')

    def test_deleting_the_professor_does_not_delete_the_group(self):
        self.group.head_professor = self.professor
        self.group.save(update_fields=['head_professor'])
        self.professor.delete()
        self.group.refresh_from_db()
        self.assertTrue(
            AcademicGroup.objects.filter(pk=self.group.pk).exists())
        self.assertIsNone(self.group.head_professor)


class GroupHeadOnThePagesTests(TestCase):
    """آنچه ثبت شد باید روی هر سه صفحه دیده شود."""

    def setUp(self):
        cache.clear()
        faculty = Department.objects.create(
            name='دانشکده فنی', slug='fanni', is_active=True)
        self.professor = Professor.objects.create(
            first_name='مریم', last_name='رضایی', slug='maryam-rezaee',
            department=faculty, rank='associate')
        self.group = AcademicGroup.objects.create(
            name='گروه کامپیوتر', slug='computer', department=faculty,
            is_active=True, head_professor=self.professor)

    def test_the_groups_list_shows_the_head(self):
        html = self.client.get(
            reverse('academics:groups_list')).content.decode()
        self.assertIn('مریم رضایی', html)
        self.assertIn('مدیر گروه', html)

    def test_the_group_page_shows_the_head(self):
        html = self.client.get(self.group.get_absolute_url()).content.decode()
        self.assertIn('مریم رضایی', html)
        self.assertIn('دانشیار', html)

    def test_the_group_page_links_to_the_professor(self):
        html = self.client.get(self.group.get_absolute_url()).content.decode()
        self.assertIn(self.professor.get_absolute_url(), html)

    def test_the_professor_page_says_which_group_they_head(self):
        """پیش از این فقط از سمت گروه دیده می‌شد."""
        html = self.client.get(
            self.professor.get_absolute_url()).content.decode()
        self.assertIn('prof-head-badge', html)
        self.assertIn('گروه کامپیوتر', html)

    def test_an_inactive_group_is_not_advertised_on_the_professor_page(self):
        self.group.is_active = False
        self.group.save(update_fields=['is_active'])
        cache.clear()
        html = self.client.get(
            self.professor.get_absolute_url()).content.decode()
        self.assertNotIn('prof-head-badge', html)

    def test_a_group_without_a_head_shows_no_empty_card(self):
        self.group.head_professor = None
        self.group.save(update_fields=['head_professor'])
        cache.clear()
        html = self.client.get(
            reverse('academics:groups_list')).content.decode()
        self.assertNotIn('grp-head-role', html)


class GroupHeadReportTests(TestCase):
    """مدیر باید بداند کدام گروه هنوز مدیر ندارد."""

    def setUp(self):
        cache.clear()
        self.faculty = Department.objects.create(
            name='دانشکده فنی', slug='fanni', is_active=True)
        self.group = AcademicGroup.objects.create(
            name='گروه کامپیوتر', slug='computer',
            department=self.faculty, is_active=True)

    def _run(self, *args):
        out = StringIO()
        call_command('check_group_heads', *args, stdout=out)
        return out.getvalue()

    def test_a_group_without_a_head_is_reported(self):
        output = self._run()
        self.assertIn('گروه کامپیوتر', output)
        self.assertIn('بدون مدیر', output)

    def test_a_linked_head_is_counted_separately(self):
        professor = Professor.objects.create(
            first_name='مریم', last_name='رضایی', slug='m-r',
            department=self.faculty, rank='associate')
        self.group.head_professor = professor
        self.group.save(update_fields=['head_professor'])
        self.assertIn('به پروندهٔ هیئت علمی وصل', self._run())

    def test_a_manual_name_is_flagged_as_unlinked(self):
        """نام دستی کار می‌کند، ولی مدیر باید بداند وصل نیست."""
        self.group.head = 'دکتر احمدی'
        self.group.save(update_fields=['head'])
        self.assertIn('وصل نیست', self._run())

    def test_suggestions_come_from_the_same_faculty(self):
        Professor.objects.create(
            first_name='علی', last_name='کریمی', slug='a-k',
            department=self.faculty, rank='professor')
        output = self._run('--suggest')
        self.assertIn('پیشنهاد', output)
        self.assertIn('علی کریمی', output)

    def test_it_suggests_nothing_it_cannot_know(self):
        """«مدیر گروه کیست» را فقط موسسه می‌داند."""
        Professor.objects.create(
            first_name='علی', last_name='کریمی', slug='a-k',
            department=self.faculty, rank='professor')
        self._run('--suggest')
        self.group.refresh_from_db()
        self.assertIsNone(self.group.head_professor)

    def test_no_groups_says_so(self):
        AcademicGroup.objects.all().delete()
        self.assertIn('گروهی ثبت نشده', self._run())
