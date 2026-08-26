"""رشته‌های دانشکده باید زیر گروه خودشان دسته‌بندی شوند."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicGroup, Department, Major


class DepartmentMajorGroupingTests(TestCase):
    """۲۷ رشته در یک شبکه، دیواری از کارت بود."""

    @classmethod
    def setUpTestData(cls):
        cls.faculty = Department.objects.create(
            name='دانشکده مدیریت', slug='modiriat', is_active=True)
        cls.accounting = AcademicGroup.objects.create(
            name='گروه حسابداری', slug='hesab', department=cls.faculty,
            order=1, is_active=True)
        cls.business = AcademicGroup.objects.create(
            name='گروه بازرگانی', slug='bazargani', department=cls.faculty,
            order=2, is_active=True)

        Major.objects.create(
            name='حسابداری', slug='m1', degree='bachelor_cont',
            department=cls.faculty, group=cls.accounting, is_active=True)
        Major.objects.create(
            name='حسابداری مالی', slug='m2', degree='associate_cont',
            department=cls.faculty, group=cls.accounting, is_active=True)
        Major.objects.create(
            name='مدیریت بازرگانی', slug='m3', degree='bachelor_cont',
            department=cls.faculty, group=cls.business, is_active=True)

    def setUp(self):
        cache.clear()

    def _html(self):
        return self.client.get(self.faculty.get_absolute_url()).content.decode()

    def _majors(self):
        """فقط بخش رشته‌ها.

        نوار بالای سایت همهٔ گروه‌ها را فهرست می‌کند، پس جست‌وجوی نام
        گروه در کل صفحه همیشه اول به منو می‌خورد، نه به بلوک رشته‌ها.
        """
        html = self._html()
        return html.split('رشته‌های تحصیلی')[1].split('اعضای هیئت علمی')[0]

    def test_the_page_opens(self):
        self.assertEqual(
            self.client.get(self.faculty.get_absolute_url()).status_code, 200)

    def test_majors_are_grouped(self):
        html = self._html()
        self.assertEqual(html.count('data-major-group'), 2)

    def test_each_group_holds_its_own(self):
        html = self._majors()
        block = html.split('گروه حسابداری')[1].split('data-major-group')[0]
        self.assertIn('حسابداری مالی', block)
        self.assertNotIn('مدیریت بازرگانی', block)

    def test_the_group_order_is_honoured(self):
        html = self._majors()
        self.assertLess(html.index('گروه حسابداری'),
                        html.index('گروه بازرگانی'))

    def test_each_group_shows_its_count(self):
        html = self._majors()
        block = html.split('گروه حسابداری')[1][:400]
        self.assertIn('2 رشته', block)

    def test_the_group_name_links_to_its_page(self):
        html = self._html()
        self.assertIn(self.accounting.get_absolute_url(), html)

    def test_only_the_degrees_present_are_offered(self):
        """فیلتر نباید مقطعی را پیشنهاد دهد که در این دانشکده نیست."""
        html = self._html()
        bar = html.split('data-degree-filter')[1].split('</div>')[0]
        self.assertIn('data-degree="bachelor_cont"', bar)
        self.assertIn('data-degree="associate_cont"', bar)
        self.assertNotIn('data-degree="master"', bar)

    def test_every_card_carries_its_degree(self):
        html = self._html()
        self.assertEqual(html.count('class="mj-card" data-degree='), 3)

    def test_all_majors_are_rendered_without_javascript(self):
        """فیلتر سمت کاربر است؛ بدون آن هیچ رشته‌ای نباید غایب باشد."""
        html = self._html()
        for name in ('حسابداری', 'حسابداری مالی', 'مدیریت بازرگانی'):
            self.assertIn(name, html)

    def test_a_major_without_a_group_still_appears(self):
        Major.objects.create(
            name='رشتهٔ بی‌گروه', slug='m4', degree='bachelor_cont',
            department=self.faculty, group=None, is_active=True)
        html = self._html()
        self.assertIn('رشتهٔ بی‌گروه', html)
        self.assertIn('بدون گروه', html)

    def test_an_empty_group_is_not_drawn(self):
        """گروهی که رشته ندارد، بلوک خالی نمی‌سازد.

        فقط بخش رشته‌ها سنجیده می‌شود: نوار بالای سایت همهٔ گروه‌ها
        را فهرست می‌کند و جست‌وجو در کل صفحه همیشه پیدایش می‌کند.
        """
        AcademicGroup.objects.create(
            name='گروه خالی', slug='khali', department=self.faculty,
            order=3, is_active=True)
        self.assertNotIn('گروه خالی', self._majors())

    def test_an_inactive_major_is_left_out(self):
        Major.objects.create(
            name='رشتهٔ بسته', slug='m5', degree='bachelor_cont',
            department=self.faculty, group=self.accounting, is_active=False)
        self.assertNotIn('رشتهٔ بسته', self._html())

    def test_a_single_degree_hides_the_filter(self):
        """یک دکمه در کنار «همه» چیزی به کسی نمی‌گوید."""
        Major.objects.filter(degree='associate_cont').delete()
        cache.clear()
        self.assertNotIn('data-degree-filter', self._html())

    def test_the_filter_is_progressive(self):
        from pathlib import Path
        from django.conf import settings
        js = (Path(settings.BASE_DIR) / 'static' / 'js' / 'main.js').read_text(
            encoding='utf-8')
        self.assertIn('data-degree-filter', js)
        self.assertIn('[data-major-group]', js)
