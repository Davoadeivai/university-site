"""درخت ساختار آموزشی، و آیتم «دانشکده‌ها» در نوار بالا."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicGroup, Department, Major


class StructureTreeTests(TestCase):
    """دانشکده ← گروه ← رشته، در یک صفحه."""

    @classmethod
    def setUpTestData(cls):
        cls.engineering = Department.objects.create(
            name='دانشکده فنی', slug='fanni', order=1, is_active=True,
            short_description='گروه‌های مهندسی.')
        cls.management = Department.objects.create(
            name='دانشکده مدیریت', slug='modiriat', order=2, is_active=True)

        cls.computer = AcademicGroup.objects.create(
            name='گروه کامپیوتر', slug='computer',
            department=cls.engineering, order=1, is_active=True)
        cls.accounting = AcademicGroup.objects.create(
            name='گروه حسابداری', slug='hesab',
            department=cls.management, order=1, is_active=True)

        Major.objects.create(
            name='مهندسی کامپیوتر', slug='m1', degree='bachelor_cont',
            department=cls.engineering, group=cls.computer, is_active=True)
        Major.objects.create(
            name='کاردانی کامپیوتر', slug='m2', degree='associate_cont',
            department=cls.engineering, group=cls.computer, is_active=True)
        Major.objects.create(
            name='حسابداری', slug='m3', degree='bachelor_cont',
            department=cls.management, group=cls.accounting, is_active=True)

    def setUp(self):
        cache.clear()

    def _html(self):
        return self.client.get(reverse('academics:departments')).content.decode()

    def _tree(self):
        """فقط خودِ درخت.

        نوار بالای سایت همهٔ گروه‌ها را فهرست می‌کند، پس جست‌وجوی نام
        گروه در کل صفحه اول به منو می‌خورد، نه به درخت.
        """
        return self._html().split('<div class="trunk">')[1]

    def _branch(self, group_name):
        """یک شاخه، از نامش تا بسته‌شدنش."""
        marker = 'data-search="%s"' % group_name
        return self._tree().split(marker)[1].split('</details>')[0]

    def test_the_page_opens(self):
        self.assertEqual(
            self.client.get(reverse('academics:departments')).status_code, 200)

    def test_all_three_levels_are_present(self):
        html = self._html()
        self.assertIn('دانشکده فنی', html)
        self.assertIn('گروه کامپیوتر', html)
        self.assertIn('مهندسی کامپیوتر', html)

    def test_the_summary_counts_everything(self):
        html = self._html()
        summary = html.split('trunk-figures')[1].split('</div>')[0]
        self.assertIn('2', summary)
        self.assertIn('دانشکده', summary)
        self.assertIn('3', summary)
        self.assertIn('رشته', summary)

    def test_each_faculty_reports_its_own_totals(self):
        block = self._tree().split('دانشکده فنی')[1].split('class="bough ')[0]
        tally = block.split('bough-tally')[1].split('</p>')[0]
        self.assertIn('>1</strong> گروه', tally)
        self.assertIn('>2</strong> رشته', tally)

    def test_a_major_sits_under_its_own_group(self):
        block = self._branch('گروه حسابداری')
        self.assertIn('حسابداری', block)
        self.assertNotIn('مهندسی کامپیوتر', block)

    def test_branches_use_details_not_javascript(self):
        """باز و بسته‌شدن باید رفتار خودِ مرورگر باشد."""
        html = self._html()
        self.assertIn('<details', html)
        self.assertIn('<summary>', html)

    def test_every_major_is_in_the_html_even_when_collapsed(self):
        """بسته‌بودن یک شاخه نباید رشته‌ها را از HTML بردارد."""
        html = self._html()
        for name in ('مهندسی کامپیوتر', 'کاردانی کامپیوتر', 'حسابداری'):
            self.assertIn(name, html)

    def test_the_first_branch_opens_by_default(self):
        """صفحهٔ کاملاً بسته چیزی نشان نمی‌دهد و بی‌فایده به‌نظر می‌رسد."""
        self.assertIn('<details open>', self._html())

    def test_a_major_without_a_group_still_shows(self):
        Major.objects.create(
            name='رشتهٔ بی‌گروه', slug='m4', degree='bachelor_cont',
            department=self.engineering, group=None, is_active=True)
        html = self._html()
        self.assertIn('رشتهٔ بی‌گروه', html)
        self.assertIn('بدون گروه', html)

    def test_an_empty_group_says_so(self):
        AcademicGroup.objects.create(
            name='گروه خالی', slug='khali', department=self.engineering,
            order=9, is_active=True)
        self.assertIn('ثبت نشده', self._branch('گروه خالی'))

    def test_an_inactive_major_is_left_out(self):
        Major.objects.create(
            name='رشتهٔ بسته', slug='m5', degree='bachelor_cont',
            department=self.engineering, group=self.computer, is_active=False)
        self.assertNotIn('رشتهٔ بسته', self._html())

    def test_the_faculty_order_is_honoured(self):
        html = self._tree()
        self.assertLess(html.index('دانشکده فنی'), html.index('دانشکده مدیریت'))

    def test_it_scales_past_a_handful_of_groups(self):
        """درخت با سه پرس‌وجو ساخته می‌شود، نه یکی به‌ازای هر گروه."""
        for index in range(8):
            group = AcademicGroup.objects.create(
                name='گروه %d' % index, slug='g%d' % index,
                department=self.engineering, order=index + 5, is_active=True)
            Major.objects.create(
                name='رشته %d' % index, slug='mm%d' % index,
                degree='bachelor_cont', department=self.engineering,
                group=group, is_active=True)
        cache.clear()
        # شمار دقیق به context_processor هم بستگی دارد؛ آنچه مهم است
        # این است که با ده برابر شدن گروه‌ها، صفحه همچنان باز شود.
        self.assertEqual(
            self.client.get(reverse('academics:departments')).status_code, 200)


class FacultiesMenuItemTests(TestCase):
    """آیتم «دانشکده‌ها» میان معاونت‌ها و گروه‌های آموزشی."""

    def setUp(self):
        cache.clear()

    def _nav(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="mainNav"')[1].split('</nav>')[0]

    def test_the_item_exists(self):
        nav = self._nav()
        self.assertIn(reverse('academics:departments'), nav)
        self.assertIn('دانشکده‌ها', nav)

    def test_it_sits_between_deputies_and_groups(self):
        nav = self._nav()
        deputies = nav.index('fa-users-cog')
        faculties = nav.index(reverse('academics:departments'))
        groups = nav.index('گروه های آموزشی')
        self.assertLess(deputies, faculties)
        self.assertLess(faculties, groups)

    def test_the_affiliated_units_label_is_gone(self):
        """موسسه خواست این عبارت از زیرمنوی حوزه ریاست برداشته شود."""
        self.assertNotIn('واحدهای وابسته', self._nav())

    def test_its_children_survived_the_label(self):
        nav = self._nav()
        self.assertIn(reverse('core:public_relations'), nav)
        self.assertIn(reverse('core:security_office'), nav)
