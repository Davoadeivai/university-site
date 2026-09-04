"""ساختار دانشکده‌ها — سه دانشکده، یازده گروه، بدون جای‌نگهدار."""
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils.text import slugify

from academics.models import AcademicGroup, Department, Major

GROUP_NAMES = [
    'گروه برق، الکترونیک و مخابرات',
    'گروه کامپیوتر',
    'گروه معماری و نقشه‌کشی',
    'گروه مکانیک',
    'گروه حسابداری',
    'گروه مدیریت صنعتی و مالی',
    'گروه مدیریت بازرگانی',
    'گروه علوم اجتماعی',
    'گروه روان‌شناسی',
    'گروه علوم پایه و معارف',
    'گروه علوم تربیتی - مدیریت آموزشی',
]


def _run(*args):
    out = StringIO()
    call_command('set_faculties', *args, stdout=out)
    return out.getvalue()


class FacultyStructureTests(TestCase):
    """چیدن گروه‌ها زیر سه دانشکده."""

    def setUp(self):
        cache.clear()
        placeholder = Department.objects.create(
            name='تحصیلات تکمیلی', slug='takmili')
        for name in GROUP_NAMES:
            AcademicGroup.objects.create(
                name=name, slug=slugify(name, allow_unicode=True),
                department=placeholder, is_active=True)

    def test_three_faculties_are_created(self):
        _run()
        names = set(Department.objects.values_list('name', flat=True))
        self.assertEqual(names, {
            'دانشکده فنی و مهندسی',
            'دانشکده مدیریت و حسابداری',
            'دانشکده علوم تربیتی و روان‌شناسی',
        })

    def test_every_group_lands_somewhere(self):
        _run()
        self.assertEqual(
            AcademicGroup.objects.filter(department__isnull=True).count(), 0)
        total = sum(d.groups.count() for d in Department.objects.all())
        self.assertEqual(total, len(GROUP_NAMES))

    def test_engineering_gets_the_engineering_groups(self):
        _run()
        faculty = Department.objects.get(slug='fanni-mohandesi')
        names = set(faculty.groups.values_list('name', flat=True))
        self.assertEqual(len(names), 4)
        self.assertIn('گروه کامپیوتر', names)
        self.assertIn('گروه مکانیک', names)

    def test_management_and_education_are_separated(self):
        """جامعه‌شناسی زیر علوم تربیتی است.

        مدتی زیر مدیریت گذاشته شده بود؛ جدول سند «رشته‌های دانشکده‌ها»
        آن را در بلوک علوم تربیتی و روان‌شناسی می‌آورد.
        """
        _run()
        management = Department.objects.get(slug='modiriat-hesabdari')
        education = Department.objects.get(slug='olum-tarbiati-ravanshenasi')
        self.assertEqual(management.groups.count(), 3)
        self.assertEqual(education.groups.count(), 4)

        managed = set(management.groups.values_list('name', flat=True))
        taught = set(education.groups.values_list('name', flat=True))
        self.assertIn('گروه علوم اجتماعی', taught)
        self.assertIn('گروه علوم تربیتی - مدیریت آموزشی', taught)
        self.assertIn('گروه روان‌شناسی', taught)
        self.assertNotIn('گروه علوم اجتماعی', managed)
        self.assertNotIn('گروه علوم تربیتی - مدیریت آموزشی', managed)

    def test_the_third_faculty_carries_the_name_from_the_document(self):
        """پیش از رسیدن سند، نامش «علوم انسانی» بود — حدس ما."""
        _run()
        self.assertFalse(Department.objects.filter(slug='olum-ensani').exists())
        self.assertFalse(
            Department.objects.filter(name='دانشکده علوم انسانی').exists())

    def test_the_old_row_is_renamed_not_duplicated(self):
        """ساختن ردیف تازه، ردیف قدیمی را با گروه‌هایش رها می‌کرد."""
        _run()
        old = Department.objects.create(
            name='دانشکده علوم انسانی', slug='olum-ensani')
        moved = AcademicGroup.objects.get(name='گروه روان‌شناسی')
        moved.department = old
        moved.save(update_fields=['department'])
        Department.objects.filter(
            slug='olum-tarbiati-ravanshenasi').delete()

        _run()
        self.assertEqual(
            Department.objects.filter(
                name__contains='علوم تربیتی').count(), 1)
        self.assertFalse(Department.objects.filter(slug='olum-ensani').exists())

    def test_a_group_in_the_wrong_managed_faculty_is_corrected(self):
        """گروهی که زیر یکی از همین سه دانشکده اشتباه نشسته، اصلاح شود."""
        _run()
        social = AcademicGroup.objects.get(name='گروه علوم اجتماعی')
        social.department = Department.objects.get(slug='modiriat-hesabdari')
        social.save(update_fields=['department'])

        _run()
        social.refresh_from_db()
        self.assertEqual(social.department.slug,
                         'olum-tarbiati-ravanshenasi')

    def test_the_placeholder_is_removed_once_empty(self):
        _run()
        self.assertFalse(Department.objects.filter(slug='takmili').exists())

    def test_a_placeholder_with_content_is_kept(self):
        """برداشتن ردیفی که هنوز رشته دارد، رشته‌ها را هم می‌برد."""
        placeholder = Department.objects.get(slug='takmili')
        Major.objects.create(
            name='رشتهٔ یتیم', slug='yatim', degree='bachelor_cont',
            department=placeholder)
        report = _run()
        self.assertTrue(Department.objects.filter(slug='takmili').exists())
        self.assertIn('هنوز محتوا دارد', report)

    def test_majors_follow_their_group(self):
        group = AcademicGroup.objects.get(name='گروه کامپیوتر')
        placeholder = Department.objects.get(slug='takmili')
        major = Major.objects.create(
            name='مهندسی کامپیوتر', slug='computer', degree='bachelor_cont',
            department=placeholder, group=group)
        _run()
        major.refresh_from_db()
        self.assertEqual(major.department.slug, 'fanni-mohandesi')

    def test_running_twice_moves_nothing_the_second_time(self):
        _run()
        report = _run()
        self.assertIn('0 گروه جابه‌جا شد', report)

    def test_dry_run_changes_nothing(self):
        before = list(AcademicGroup.objects.values_list('department_id', flat=True))
        _run('--dry-run')
        after = list(AcademicGroup.objects.values_list('department_id', flat=True))
        self.assertEqual(before, after)

    def test_an_admin_move_is_respected(self):
        """گروهی که ادمین جای دیگری برده، بی‌اجازه برنمی‌گردد."""
        _run()
        elsewhere = Department.objects.create(name='دانشکده تازه', slug='new')
        group = AcademicGroup.objects.get(name='گروه کامپیوتر')
        group.department = elsewhere
        group.save(update_fields=['department'])

        _run()
        group.refresh_from_db()
        self.assertEqual(group.department, elsewhere)

        _run('--force')
        group.refresh_from_db()
        self.assertEqual(group.department.slug, 'fanni-mohandesi')

    def test_it_says_so_when_there_are_no_groups(self):
        AcademicGroup.objects.all().delete()
        self.assertIn('هیچ گروهی ثبت نشده', _run())

    def test_an_unmatched_group_is_reported(self):
        AcademicGroup.objects.create(
            name='گروه موسیقی', slug='music',
            department=Department.objects.get(slug='takmili'))
        self.assertIn('به هیچ دانشکده‌ای نخورد', _run())


class FacultiesOnTheHomePageTests(TestCase):
    """صفحهٔ اصلی باید دانشکده‌ها را با گروه‌هایشان نشان دهد."""

    def setUp(self):
        cache.clear()
        placeholder = Department.objects.create(
            name='تحصیلات تکمیلی', slug='takmili')
        for name in GROUP_NAMES:
            AcademicGroup.objects.create(
                name=name, slug=slugify(name, allow_unicode=True),
                department=placeholder, is_active=True)
        _run()
        cache.clear()

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_all_three_are_shown(self):
        html = self._html()
        for name in ('دانشکده فنی و مهندسی',
                     'دانشکده مدیریت و حسابداری',
                     'دانشکده علوم تربیتی و روان‌شناسی'):
            self.assertIn(name, html)

    def test_each_card_lists_its_groups(self):
        html = self._html()
        self.assertIn('گروه کامپیوتر', html)
        self.assertIn('fac-groups', html)

    def test_the_counts_are_shown(self):
        html = self._html()
        self.assertIn('گروه آموزشی ·', html)

    def test_each_card_gets_its_own_colour(self):
        html = self._html()
        for n in (1, 2, 3):
            self.assertIn('fac-card-%d' % n, html)

    def test_no_faculties_leaves_the_section_clean(self):
        """جای خالی فقط به کارکنان گفته می‌شود، نه به بازدیدکننده."""
        from django.contrib.auth.models import User

        Department.objects.all().delete()
        cache.clear()
        html = self._html()
        self.assertNotIn('fac-card', html)
        self.assertNotIn('دانشکده فنی', html)

        User.objects.create_user('kar4', password='Str0ng!Pass2026',
                                 is_staff=True)
        self.client.login(username='kar4', password='Str0ng!Pass2026')
        cache.clear()
        self.assertIn('دانشکده‌ای', self._html())


class GeneralFacultyIsNotAFacultyTests(TestCase):
    """وضعیت واقعی سرور: «دانشکده عمومی» همهٔ گروه‌ها را گرفته بود.

    سه دانشکدهٔ واقعی صفر گروه نشان می‌دادند و یک «دانشکده عمومی»
    که موسسه اصلاً ندارد، یازده گروه زیرش بود. دستور دست نمی‌زد،
    چون آن ردیف را یک انتخاب عمدی مدیر می‌دید.
    """

    def setUp(self):
        cache.clear()
        self.general = Department.objects.create(
            name='دانشکده عمومی', slug='omoomi', order=1, is_active=True)
        for name in GROUP_NAMES:
            AcademicGroup.objects.create(
                name=name, slug=slugify(name, allow_unicode=True),
                department=self.general, is_active=True)

    def test_the_groups_are_taken_out_of_it(self):
        _run()
        self.assertEqual(self.general.groups.count(), 0)

    def test_it_is_removed_once_it_is_empty(self):
        _run()
        self.assertFalse(
            Department.objects.filter(name='دانشکده عمومی').exists())

    def test_every_group_lands_in_a_real_faculty(self):
        _run()
        for name in GROUP_NAMES:
            group = AcademicGroup.objects.get(name=name)
            self.assertIsNotNone(group.department, name)
            self.assertNotEqual(group.department.name, 'دانشکده عمومی', name)

    def test_the_real_faculties_stop_showing_zero_groups(self):
        """روی سرور هر سه، صفر گروه نشان می‌دادند."""
        _run()
        for slug in ('fanni-mohandesi', 'modiriat-hesabdari',
                     'olum-tarbiati-ravanshenasi'):
            faculty = Department.objects.get(slug=slug)
            self.assertGreater(faculty.groups.count(), 0, slug)

    def test_a_faculty_the_document_names_is_never_treated_as_a_placeholder(self):
        """«عمومی» نباید با «دانشکده فنی و مهندسی» اشتباه گرفته شود."""
        _run()
        self.assertEqual(Department.objects.filter(is_active=True).count(), 3)

    def test_a_group_an_admin_moved_elsewhere_is_still_respected(self):
        """محافظِ تصمیم مدیر نباید با این اصلاح از بین برود."""
        _run()
        elsewhere = Department.objects.create(
            name='دانشکده تازه', slug='new-one')
        group = AcademicGroup.objects.get(name='گروه کامپیوتر')
        group.department = elsewhere
        group.save(update_fields=['department'])

        _run()
        group.refresh_from_db()
        self.assertEqual(group.department, elsewhere)
