"""مسیر سلسله‌مراتبی و معرفی رئیس دانشکده."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicGroup, Department, Major


class HierarchicalBreadcrumbTests(TestCase):
    """صفحهٔ رشته فقط «صفحه اصلی» را داشت و راهی به بالا نبود."""

    @classmethod
    def setUpTestData(cls):
        cls.faculty = Department.objects.create(
            name='دانشکده فنی', slug='fanni', order=1, is_active=True)
        cls.group = AcademicGroup.objects.create(
            name='گروه کامپیوتر', slug='computer',
            department=cls.faculty, order=1, is_active=True)
        cls.major = Major.objects.create(
            name='مهندسی کامپیوتر', slug='m1', degree='bachelor_cont',
            department=cls.faculty, group=cls.group, is_active=True)

    def setUp(self):
        cache.clear()

    def _crumbs(self, url):
        html = self.client.get(url).content.decode()
        return html.split('<ol class="breadcrumb">')[1].split('</ol>')[0]

    def test_a_major_shows_its_whole_line(self):
        crumbs = self._crumbs(reverse('academics:major_detail',
                                      args=[self.major.slug]))
        for text in ('صفحه اصلی', 'دانشکده‌ها', 'دانشکده فنی',
                     'گروه کامپیوتر', 'مهندسی کامپیوتر'):
            self.assertIn(text, crumbs)

    def test_each_ancestor_is_a_way_back_up(self):
        crumbs = self._crumbs(reverse('academics:major_detail',
                                      args=[self.major.slug]))
        self.assertIn(self.faculty.get_absolute_url(), crumbs)
        self.assertIn(self.group.get_absolute_url(), crumbs)
        self.assertIn(reverse('academics:departments'), crumbs)

    def test_the_current_page_is_not_a_link(self):
        crumbs = self._crumbs(reverse('academics:major_detail',
                                      args=[self.major.slug]))
        last = crumbs.split('<li')[-1]
        self.assertIn('aria-current="page"', last)
        self.assertNotIn('<a', last)

    def test_a_group_shows_its_faculty(self):
        crumbs = self._crumbs(self.group.get_absolute_url())
        self.assertIn('دانشکده فنی', crumbs)
        self.assertIn(self.faculty.get_absolute_url(), crumbs)

    def test_a_faculty_stops_at_the_faculties_page(self):
        crumbs = self._crumbs(self.faculty.get_absolute_url())
        self.assertIn(reverse('academics:departments'), crumbs)
        self.assertIn('دانشکده فنی', crumbs)
        self.assertNotIn('گروه کامپیوتر', crumbs)

    def test_a_major_without_a_group_skips_that_rung(self):
        """حلقهٔ نبوده باید بیفتد، نه اینکه جای خالی بگذارد."""
        loose = Major.objects.create(
            name='رشتهٔ بی‌گروه', slug='m2', degree='bachelor_cont',
            department=self.faculty, group=None, is_active=True)
        crumbs = self._crumbs(reverse('academics:major_detail',
                                      args=[loose.slug]))
        self.assertIn('دانشکده فنی', crumbs)
        self.assertIn('رشتهٔ بی‌گروه', crumbs)
        self.assertNotIn('<li class="breadcrumb-item">\n            <a href=""',
                         crumbs)


class FacultyDeanTests(TestCase):
    """هر دانشکده رئیسی دارد؛ تا امروز فقط یک خط متن در کنار بود."""

    @classmethod
    def setUpTestData(cls):
        cls.faculty = Department.objects.create(
            name='دانشکده فنی', slug='fanni', order=1, is_active=True,
            head='دکتر مریم رضایی', head_title='دانشیار گروه کامپیوتر')
        AcademicGroup.objects.create(
            name='گروه کامپیوتر', slug='computer',
            department=cls.faculty, order=1, is_active=True)

    def setUp(self):
        cache.clear()

    def _tree(self):
        html = self.client.get(
            reverse('academics:departments')).content.decode()
        return html.split('<div class="tree">')[1]

    def test_the_dean_appears_on_the_tree(self):
        tree = self._tree()
        self.assertIn('دکتر مریم رضایی', tree)
        self.assertIn('دانشیار گروه کامپیوتر', tree)
        self.assertIn('رئیس دانشکده', tree)

    def test_the_dean_appears_on_the_faculty_page(self):
        html = self.client.get(self.faculty.get_absolute_url()).content.decode()
        self.assertIn('دکتر مریم رضایی', html)
        self.assertIn('tree-dean', html)

    def test_no_photo_leaves_a_placeholder_not_a_broken_image(self):
        tree = self._tree()
        self.assertIn('tree-dean-blank', tree)
        self.assertNotIn('<img class="tree-dean-photo"', tree)

    def test_a_photo_is_used_when_there_is_one(self):
        self.faculty.head_photo = 'departments/heads/rezaee.jpg'
        self.faculty.save(update_fields=['head_photo'])
        cache.clear()
        tree = self._tree()
        self.assertIn('rezaee.jpg', tree)
        self.assertNotIn('tree-dean-blank', tree)

    def test_a_photo_declares_its_size(self):
        """بدون width/height صفحه پس از رسیدن عکس یک تکان می‌خورد."""
        self.faculty.head_photo = 'departments/heads/rezaee.jpg'
        self.faculty.save(update_fields=['head_photo'])
        cache.clear()
        img = self._tree().split('<img class="tree-dean-photo"')[1].split('>')[0]
        self.assertIn('width="44"', img)
        self.assertIn('height="44"', img)

    def test_no_dean_means_no_block(self):
        self.faculty.head = ''
        self.faculty.save(update_fields=['head'])
        cache.clear()
        self.assertNotIn('tree-dean', self._tree())

    def test_a_dean_without_a_title_still_shows(self):
        self.faculty.head_title = ''
        self.faculty.save(update_fields=['head_title'])
        cache.clear()
        tree = self._tree()
        self.assertIn('دکتر مریم رضایی', tree)
        self.assertNotIn('tree-dean-title', tree)

    def test_the_panel_offers_both_new_fields(self):
        from academics.admin import DepartmentAdmin
        from django.contrib import admin as dj_admin

        model_admin = DepartmentAdmin(Department, dj_admin.site)
        fields = model_admin.get_fields(None)
        self.assertIn('head_photo', fields)
        self.assertIn('head_title', fields)
