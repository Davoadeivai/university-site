"""ترتیب گروه‌های آموزشی در منو."""
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils.text import slugify

from academics.models import AcademicGroup, Department

NAMES = [
    'گروه برق، الکترونیک و مخابرات',
    'گروه کامپیوتر',
    'گروه معماری و نقشه کشی',
    'گروه مکانیک',
    'گروه حسابداری',
    'گروه مدیریت صنعتی و مالی',
    'گروه مدیریت بازرگانی',
    'گروه علوم اجتماعی',
    'گروه روانشناسی',
    'گروه علوم پایه و معارف',
    'گروه علوم تربیتی - مدیریت آموزشی',
]

WANTED_FIRST = [
    'گروه مدیریت صنعتی و مالی',
    'گروه مدیریت بازرگانی',
    'گروه علوم تربیتی - مدیریت آموزشی',
]


def _run(*args):
    out = StringIO()
    call_command('set_group_order', *args, stdout=out)
    return out.getvalue()


class GroupOrderTests(TestCase):
    """موسسه سه گروه اول را تعیین کرد؛ بقیه پس از آن‌ها."""

    def setUp(self):
        cache.clear()
        faculty = Department.objects.create(
            name='دانشکده', slug='d', is_active=True)
        for index, name in enumerate(NAMES, start=1):
            AcademicGroup.objects.create(
                name=name, slug=slugify(name, allow_unicode=True),
                department=faculty, order=index, is_active=True)

    def _ordered(self):
        return list(AcademicGroup.objects.order_by('order')
                    .values_list('name', flat=True))

    def test_the_three_the_institute_named_come_first(self):
        _run()
        self.assertEqual(self._ordered()[:3], WANTED_FIRST)

    def test_the_rest_keep_their_previous_order(self):
        """جابه‌جایی بی‌دلیل بقیه، خواستهٔ موسسه نبود."""
        _run()
        rest = self._ordered()[3:]
        previous = [n for n in NAMES if n not in WANTED_FIRST]
        self.assertEqual(rest, previous)

    def test_nobody_is_lost(self):
        _run()
        self.assertEqual(sorted(self._ordered()), sorted(NAMES))

    def test_the_menu_shows_the_same_order(self):
        _run()
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        # زیرمنوی خودِ «گروه‌های آموزشی»، نه هم‌نامش در منوی معاونت
        block = html.split('nav-dd-groups')[1].split('</ul>')[0]
        positions = [block.index(name) for name in WANTED_FIRST]
        self.assertEqual(positions, sorted(positions))

    def test_running_twice_changes_nothing_the_second_time(self):
        _run()
        first = self._ordered()
        _run()
        self.assertEqual(self._ordered(), first)

    def test_dry_run_writes_nothing(self):
        before = self._ordered()
        _run('--dry-run')
        self.assertEqual(self._ordered(), before)

    def test_a_new_group_goes_to_the_end(self):
        _run()
        faculty = Department.objects.first()
        AcademicGroup.objects.create(
            name='گروه تازه', slug='taze', department=faculty,
            order=99, is_active=True)
        _run()
        self.assertEqual(self._ordered()[-1], 'گروه تازه')

    def test_it_says_so_when_there_are_no_groups(self):
        AcademicGroup.objects.all().delete()
        self.assertIn('گروهی ثبت نشده', _run())

    def test_a_missing_name_is_reported_not_crashed(self):
        AcademicGroup.objects.filter(
            name='گروه مدیریت بازرگانی').delete()
        output = _run()
        self.assertIn('پیدا نشد', output)
        self.assertEqual(self._ordered()[0], 'گروه مدیریت صنعتی و مالی')
