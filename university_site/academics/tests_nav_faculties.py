"""منوی دانشکده‌ها با رشته‌ها، و صفحهٔ مدیران گروه‌ها."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicGroup, Department, Major


def _build():
    fanni = Department.objects.create(
        name='دانشکده فنی و مهندسی', slug='fanni', order=1, is_active=True)
    modiriat = Department.objects.create(
        name='دانشکده مدیریت و حسابداری', slug='modiriat', order=2,
        is_active=True)
    group = AcademicGroup.objects.create(
        department=fanni, name='گروه کامپیوتر', slug='computer', order=1,
        is_active=True, head='دکتر نمونه')
    AcademicGroup.objects.create(
        department=modiriat, name='گروه حسابداری', slug='hesabdari', order=1,
        is_active=True)
    Major.objects.create(
        department=fanni, group=group, name='مهندسی کامپیوتر',
        slug='mohandesi-computer', degree='bachelor_cont', is_active=True)
    Major.objects.create(
        department=modiriat, name='حسابداری', slug='hesabdari-ارشد',
        degree='master', is_active=True)
    return fanni, modiriat


class FacultyMenuTests(TestCase):
    """رسیدن به یک رشته، دو صفحه فاصله داشت."""

    def setUp(self):
        cache.clear()
        self.fanni, self.modiriat = _build()

    def _nav(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="mainNav"')[1].split('</nav>')[0]

    def test_each_faculty_is_listed(self):
        nav = self._nav()
        self.assertIn('دانشکده فنی و مهندسی', nav)
        self.assertIn('دانشکده مدیریت و حسابداری', nav)

    def test_each_major_hangs_under_its_faculty(self):
        block = self._nav().split('nav-dd-faculties')[1]
        self.assertIn('مهندسی کامپیوتر', block)
        self.assertIn('حسابداری', block)

    def test_a_major_leads_to_its_own_page(self):
        major = Major.objects.get(slug='mohandesi-computer')
        block = self._nav().split('nav-dd-faculties')[1]
        self.assertIn(major.get_absolute_url(), block)
        self.assertEqual(
            self.client.get(major.get_absolute_url()).status_code, 200)

    def test_the_degree_is_shown_beside_the_name(self):
        """چند رشته یک نام دارند و فقط مقطعشان فرق می‌کند."""
        block = self._nav().split('nav-dd-faculties')[1]
        self.assertIn('nav-dd-degree', block)
        self.assertIn('کارشناسی ارشد', block)

    def test_the_faculty_itself_is_still_one_click_away(self):
        block = self._nav().split('nav-dd-faculties')[1]
        self.assertIn(self.fanni.get_absolute_url(), block)
        self.assertIn(reverse('academics:departments'), block)

    def test_an_inactive_major_is_left_out(self):
        Major.objects.filter(slug='mohandesi-computer').update(is_active=False)
        cache.clear()
        block = self._nav().split('nav-dd-faculties')[1]
        self.assertNotIn('مهندسی کامپیوتر', block)


class FacultyPageListsMajorsTests(TestCase):
    """فایل PDF خواندنی بود ولی بن‌بست: اسم رشته بود، راهش نبود."""

    def setUp(self):
        cache.clear()
        _build()

    def _html(self):
        return self.client.get(
            reverse('academics:departments')).content.decode()

    def test_the_page_lists_each_faculty_with_its_majors(self):
        html = self._html()
        self.assertIn('fac-list', html)
        self.assertIn('دانشکده فنی و مهندسی', html)
        self.assertIn('مهندسی کامپیوتر', html)

    def test_each_major_is_a_link(self):
        major = Major.objects.get(slug='mohandesi-computer')
        block = self._html().split('fac-majors')[1]
        self.assertIn(major.get_absolute_url(), block)


class GroupHeadsPageTests(TestCase):
    """«مدیر گروه کامپیوتر کیست» یازده صفحه فاصله داشت."""

    def setUp(self):
        cache.clear()
        _build()

    def _html(self):
        return self.client.get(
            reverse('academics:group_heads')).content.decode()

    def test_the_page_opens(self):
        self.assertEqual(
            self.client.get(reverse('academics:group_heads')).status_code, 200)

    def test_a_group_with_a_head_shows_the_name(self):
        html = self._html()
        self.assertIn('گروه کامپیوتر', html)
        self.assertIn('دکتر نمونه', html)

    def test_a_group_without_one_says_so_instead_of_vanishing(self):
        html = self._html()
        self.assertIn('گروه حسابداری', html)
        self.assertIn('هنوز ثبت نشده', html)

    def test_the_menu_leads_to_it(self):
        html = self.client.get(reverse('core:home')).content.decode()
        nav = html.split('id="mainNav"')[1].split('</nav>')[0]
        self.assertIn(reverse('academics:group_heads'), nav)
