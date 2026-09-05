"""مرتبهٔ علمی: کارت گروه و صفحهٔ استاد باید یک چیز بگویند.

کارت مدیر گروه «دانشیار» نشان می‌داد و صفحهٔ خودِ استاد «استادیار» —
دو صفحه از یک سایت، دو حرف دربارهٔ یک نفر.
"""
from django.test import TestCase

from academics.models import AcademicGroup, Department, GroupHead
from directory.models import DirectoryPerson
from faculty.models import Professor


class TheRankReachesTheProfessorTests(TestCase):

    def setUp(self):
        faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-agree', order=1,
            is_active=True)
        self.group = AcademicGroup.objects.create(
            department=faculty, name='گروه مدیریت صنعتی و مالی',
            slug='sanati-agree', is_active=True)
        self.professor = Professor.objects.create(
            first_name='حسن', last_name='فارسیجانی', rank='assistant',
            slug='hasan-farsijani', is_active=True)

    def test_writing_it_on_the_head_updates_the_faculty_record(self):
        GroupHead.objects.create(group=self.group, professor=self.professor,
                                 rank_override='associate')
        self.professor.refresh_from_db()
        self.assertEqual(self.professor.rank, 'associate')

    def test_both_pages_then_agree(self):
        GroupHead.objects.create(group=self.group, professor=self.professor,
                                 rank_override='associate')
        group_page = self.client.get(
            self.group.get_absolute_url()).content.decode()
        self.assertIn('دانشیار', group_page)

        self.professor.refresh_from_db()
        own_page = self.client.get(
            self.professor.get_absolute_url()).content.decode()
        self.assertIn('دانشیار', own_page)
        self.assertNotIn('استادیار', own_page)

    def test_an_empty_override_changes_nothing(self):
        GroupHead.objects.create(group=self.group, professor=self.professor)
        self.professor.refresh_from_db()
        self.assertEqual(self.professor.rank, 'assistant')

    def test_a_head_without_a_faculty_record_is_harmless(self):
        GroupHead.objects.create(group=self.group, name='کسی',
                                 rank_override='professor')
        self.professor.refresh_from_db()
        self.assertEqual(self.professor.rank, 'assistant')

    def test_a_later_correction_travels_too(self):
        head = GroupHead.objects.create(
            group=self.group, professor=self.professor,
            rank_override='associate')
        head.rank_override = 'professor'
        head.save()
        self.professor.refresh_from_db()
        self.assertEqual(self.professor.rank, 'professor')


class TheDirectoryRankTravelsAtOnceTests(TestCase):
    """اصلاح در «افراد موسسه» نباید تا دیپلوی بعدی معطل بماند."""

    def setUp(self):
        self.professor = Professor.objects.create(
            first_name='حسن', last_name='فارسیجانی', rank='assistant',
            slug='hasan-f2', is_active=True)

    def test_saving_the_person_updates_the_professor(self):
        DirectoryPerson.objects.create(
            category='faculty', full_name='حسن فارسیجانی',
            academic_rank='associate')
        self.professor.refresh_from_db()
        self.assertEqual(self.professor.rank, 'associate')

    def test_an_empty_rank_leaves_it_alone(self):
        DirectoryPerson.objects.create(
            category='faculty', full_name='حسن فارسیجانی')
        self.professor.refresh_from_db()
        self.assertEqual(self.professor.rank, 'assistant')

    def test_an_unknown_name_is_harmless(self):
        DirectoryPerson.objects.create(
            category='faculty', full_name='کس دیگری',
            academic_rank='professor')
        self.professor.refresh_from_db()
        self.assertEqual(self.professor.rank, 'assistant')

    def test_spacing_differences_do_not_stop_it(self):
        DirectoryPerson.objects.create(
            category='faculty', full_name='حسن   فارسیجانی',
            academic_rank='associate')
        self.professor.refresh_from_db()
        self.assertEqual(self.professor.rank, 'associate')
