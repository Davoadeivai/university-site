"""ادغام رشته‌های تکراری."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from academics.models import AcademicGroup, Course, Department, Major


def _run(*args):
    out = StringIO()
    call_command('merge_duplicate_majors', *args, stdout=out)
    return out.getvalue()


class MergeDuplicateMajorTests(TestCase):
    """ده رشته دو بار ثبت شده بودند و دو ردیف پشت سر هم دیده می‌شدند."""

    def setUp(self):
        self.faculty = Department.objects.create(
            name='دانشکده مدیریت و حسابداری', slug='modiriat')
        self.group = AcademicGroup.objects.create(
            name='گروه حسابداری', slug='hesab', department=self.faculty)

    def _major(self, slug, **extra):
        return Major.objects.create(
            name='حسابداری - حسابداری', slug=slug, degree='master',
            department=self.faculty, group=self.group, is_active=True,
            **extra)

    def test_nothing_to_do_says_so(self):
        self._major('a')
        self.assertIn('تکراری‌ای نیست', _run())

    def test_a_duplicate_pair_becomes_one(self):
        self._major('a')
        self._major('b')
        _run()
        self.assertEqual(Major.objects.count(), 1)

    def test_the_same_name_at_another_degree_is_not_a_duplicate(self):
        """«حسابداری» در ارشد و کاردانی، دو رشتهٔ جداست."""
        self._major('a')
        Major.objects.create(
            name='حسابداری - حسابداری', slug='b', degree='associate_cont',
            department=self.faculty, group=self.group)
        _run()
        self.assertEqual(Major.objects.count(), 2)

    def test_spelling_differences_still_count_as_the_same(self):
        """نیم‌فاصله و «ي» عربی نباید یک رشته را دو رشته نشان دهد."""
        self._major('a')
        Major.objects.create(
            name='حسابداري – حسابداری', slug='b', degree='master',
            department=self.faculty, group=self.group)
        _run()
        self.assertEqual(Major.objects.count(), 1)

    def test_the_fuller_row_survives(self):
        self._major('thin')
        self._major('rich', description='معرفی رشته', code='1234')
        _run()
        self.assertEqual(Major.objects.get().slug, 'rich')

    def test_the_survivor_takes_the_readable_address(self):
        """محتوا در یک ردیف بود و نشانی خوانا در دیگری."""
        self._major('hesabdari-arshad')
        self._major('master-1-5748df4f31', description='معرفی رشته')
        _run()
        survivor = Major.objects.get()
        self.assertEqual(survivor.slug, 'hesabdari-arshad')
        self.assertEqual(survivor.description, 'معرفی رشته')

    def test_a_readable_address_is_not_swapped_for_another(self):
        self._major('yeki', description='معرفی رشته')
        self._major('digari')
        _run()
        self.assertEqual(Major.objects.get().slug, 'yeki')

    def test_what_pointed_at_the_duplicate_now_points_at_the_survivor(self):
        keeper = self._major('keeper', description='معرفی رشته')
        extra = self._major('extra')
        course = Course.objects.create(
            name='اصول حسابداری', code='C1', credits=3, major=extra)
        _run()
        course.refresh_from_db()
        self.assertEqual(course.major_id, keeper.pk)

    def test_an_application_survives_the_merge(self):
        """درخواست پذیرش با PROTECT بسته است — حذف ساده می‌شکست."""
        from admissions.models import Application

        keeper = self._major('keeper', description='معرفی رشته')
        extra = self._major('extra')
        application = Application.objects.create(
            first_name='زهرا', last_name='محمدی', national_id='0012345678',
            degree='master', desired_major=extra)
        _run()
        application.refresh_from_db()
        self.assertEqual(application.desired_major_id, keeper.pk)
        self.assertEqual(Major.objects.count(), 1)

    def test_a_clashing_tuition_row_is_dropped_not_forced(self):
        """جدول شهریه روی (رشته، سال) یکتاست."""
        from admissions.models import TuitionStructure

        keeper = self._major('keeper', description='معرفی رشته')
        extra = self._major('extra')
        TuitionStructure.objects.create(
            major=keeper, academic_year='1404-1405', fixed_fee=1000)
        TuitionStructure.objects.create(
            major=extra, academic_year='1404-1405', fixed_fee=2000)
        _run()
        rows = TuitionStructure.objects.filter(academic_year='1404-1405')
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().major_id, keeper.pk)

    def test_a_tuition_row_for_another_year_moves_over(self):
        from admissions.models import TuitionStructure

        keeper = self._major('keeper', description='معرفی رشته')
        extra = self._major('extra')
        TuitionStructure.objects.create(
            major=extra, academic_year='1403-1404', fixed_fee=900)
        _run()
        moved = TuitionStructure.objects.get(academic_year='1403-1404')
        self.assertEqual(moved.major_id, keeper.pk)

    def test_dry_run_changes_nothing(self):
        self._major('a')
        self._major('b')
        _run('--dry-run')
        self.assertEqual(Major.objects.count(), 2)

    def test_running_twice_is_safe(self):
        self._major('a')
        self._major('b')
        _run()
        _run()
        self.assertEqual(Major.objects.count(), 1)

    def test_three_of_a_kind_collapse_to_one(self):
        self._major('a')
        self._major('b')
        self._major('c')
        _run()
        self.assertEqual(Major.objects.count(), 1)
