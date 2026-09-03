"""هم‌خوان کردن رشته‌ها با سند رسمی «رشته‌های دانشکده‌ها»."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils.text import slugify

from academics.management.commands.set_majors_from_document import (
    ALIASES, DOCUMENT, REGRADED, fold)
from academics.models import AcademicGroup, Department, Major

FACULTIES = [
    ('fanni-mohandesi', 'دانشکده فنی و مهندسی', 1),
    ('modiriat-hesabdari', 'دانشکده مدیریت و حسابداری', 2),
    ('olum-tarbiati-ravanshenasi', 'دانشکده علوم تربیتی و روان‌شناسی', 3),
]

GROUPS = [
    'گروه برق، الکترونیک و مخابرات',
    'گروه کامپیوتر',
    'گروه معماری و نقشه کشی',
    'گروه مکانیک',
    'گروه حسابداری',
    'گروه مدیریت صنعتی و مالی',
    'گروه مدیریت بازرگانی',
    'گروه علوم اجتماعی',
    'گروه روانشناسی',
    'گروه علوم تربیتی - مدیریت آموزشی',
]


def _run(*args):
    out = StringIO()
    call_command('set_majors_from_document', *args, stdout=out, stderr=out)
    return out.getvalue()


class DocumentAlignmentTests(TestCase):
    """سند مبناست: هر ردیفش باید روی سایت باشد."""

    def setUp(self):
        for slug, name, order in FACULTIES:
            Department.objects.create(
                slug=slug, name=name, order=order, is_active=True)
        engineering = Department.objects.get(slug='fanni-mohandesi')
        for index, name in enumerate(GROUPS):
            AcademicGroup.objects.create(
                name=name, slug=slugify(name, allow_unicode=True),
                department=engineering, order=index, is_active=True)

    def test_every_document_row_ends_up_on_the_site(self):
        _run()
        for name, degree, _slug, _key in DOCUMENT:
            self.assertTrue(
                Major.objects.filter(
                    name=name, degree=degree, is_active=True).exists(),
                'نیست: %s (%s)' % (name, degree))

    def test_the_counts_match_the_document(self):
        _run()
        self.assertEqual(
            Major.objects.filter(is_active=True).count(), len(DOCUMENT))

    def test_each_major_lands_in_the_faculty_the_document_names(self):
        _run()
        for name, degree, faculty_slug, _key in DOCUMENT:
            major = Major.objects.get(name=name, degree=degree)
            self.assertEqual(major.department.slug, faculty_slug, name)

    def test_a_row_outside_the_document_is_switched_off_not_deleted(self):
        """رشته با PROTECT به درخواست پذیرش بسته است؛ حذف یا می‌شکند
        یا درخواست یک داوطلب را می‌برد."""
        stray = Major.objects.create(
            name='رشتهٔ ناموجود', slug='stray', degree='master',
            department=Department.objects.first(), is_active=True)
        _run()
        stray.refresh_from_db()
        self.assertFalse(stray.is_active)

    def test_keep_extras_leaves_them_alone(self):
        stray = Major.objects.create(
            name='رشتهٔ ناموجود', slug='stray', degree='master',
            department=Department.objects.first(), is_active=True)
        _run('--keep-extras')
        stray.refresh_from_db()
        self.assertTrue(stray.is_active)

    def test_dry_run_writes_nothing(self):
        _run('--dry-run')
        self.assertEqual(Major.objects.count(), 0)

    def test_running_twice_changes_nothing_the_second_time(self):
        _run()
        first = set(Major.objects.values_list('pk', flat=True))
        _run()
        self.assertEqual(set(Major.objects.values_list('pk', flat=True)),
                         first)

    def test_it_refuses_when_the_faculties_are_missing(self):
        Department.objects.all().delete()
        self.assertIn('set_faculties', _run())


class NamePreservationTests(TestCase):
    """رشته‌ای که فقط نامش فرق دارد نباید از نو ساخته شود."""

    def setUp(self):
        for slug, name, order in FACULTIES:
            Department.objects.create(
                slug=slug, name=name, order=order, is_active=True)

    def test_an_old_name_is_renamed_not_replaced(self):
        """ساختن دوباره یعنی از دست دادن سرفصل پیوستِ ردیف قدیمی."""
        old = Major.objects.create(
            name='حسابداری - گرایش حسابرسی', slug='old-hesabrasi',
            degree='master', curriculum='متن سرفصل',
            department=Department.objects.get(slug='modiriat-hesabdari'),
            is_active=True)
        _run()
        old.refresh_from_db()
        self.assertEqual(old.name, 'حسابرسی')
        self.assertTrue(old.is_active)
        self.assertEqual(old.curriculum, 'متن سرفصل')

    def test_a_wrong_degree_is_corrected_on_the_same_row(self):
        """سند این را کاردانی ناپیوسته می‌گوید و سایت پیوسته ثبت کرده بود."""
        old = Major.objects.create(
            name='امور دولتی', slug='old-omoor', degree='associate_cont',
            department=Department.objects.get(slug='modiriat-hesabdari'),
            is_active=True)
        _run()
        old.refresh_from_db()
        self.assertEqual(old.degree, 'associate_disc')
        self.assertTrue(old.is_active)

    def test_spelling_differences_do_not_make_a_second_row(self):
        """«جامعه شناسی» و «جامعه‌شناسی» یک رشته‌اند."""
        Major.objects.create(
            name='جامعه شناسی', slug='old-jame', degree='bachelor_cont',
            department=Department.objects.get(
                slug='olum-tarbiati-ravanshenasi'),
            is_active=True)
        _run()
        self.assertEqual(
            Major.objects.filter(degree='bachelor_cont',
                                 name__contains='جامعه').count(), 1)


class DocumentTableTests(TestCase):
    """خودِ جدول‌ها باید سالم باشند."""

    def test_the_document_has_the_rows_the_pdf_lists(self):
        self.assertEqual(len(DOCUMENT), 41)

    def test_no_row_is_written_twice(self):
        keys = [(fold(name), degree) for name, degree, _s, _k in DOCUMENT]
        self.assertEqual(len(keys), len(set(keys)))

    def test_each_faculty_gets_the_share_the_pdf_gives_it(self):
        from collections import Counter

        counts = Counter(slug for _n, _d, slug, _k in DOCUMENT)
        self.assertEqual(counts['fanni-mohandesi'], 18)
        self.assertEqual(counts['modiriat-hesabdari'], 19)
        self.assertEqual(counts['olum-tarbiati-ravanshenasi'], 4)

    def test_every_alias_points_at_a_document_row(self):
        """هم‌ارزی‌ای که مقصدش در سند نیست، بی‌اثر است و گمراه‌کننده."""
        targets = {fold(name) for name, _d, _s, _k in DOCUMENT}
        for _old, _degree, new in ALIASES:
            self.assertIn(fold(new), targets, new)

    def test_every_regrade_points_at_a_document_row(self):
        rows = {(fold(name), degree) for name, degree, _s, _k in DOCUMENT}
        for _old, _wrong, new, right in REGRADED:
            self.assertIn((fold(new), right), rows, new)

    def test_no_alias_collides_with_a_document_name(self):
        """نام قدیمی که خودش در سند هست، نباید هم‌ارز چیز دیگری شود."""
        targets = {(fold(name), degree) for name, degree, _s, _k in DOCUMENT}
        for old, degree, _new in ALIASES:
            self.assertNotIn((fold(old), degree), targets, old)
