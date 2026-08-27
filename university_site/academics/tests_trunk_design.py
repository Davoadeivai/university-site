"""صفحهٔ دانشکده‌ها — نوار نسبت، ابزارها، و آنچه بدون اسکریپت کار می‌کند."""
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicGroup, Department, Major


class ProportionBarTests(TestCase):
    """پهنای هر تکه، سهم آن دانشکده از رشته‌هاست — نه تزئین."""

    @classmethod
    def setUpTestData(cls):
        cls.big = Department.objects.create(
            name='دانشکده بزرگ', slug='big', order=1, is_active=True)
        cls.small = Department.objects.create(
            name='دانشکده کوچک', slug='small', order=2, is_active=True)
        big_group = AcademicGroup.objects.create(
            name='گروه بزرگ', slug='gb', department=cls.big, is_active=True)
        small_group = AcademicGroup.objects.create(
            name='گروه کوچک', slug='gk', department=cls.small, is_active=True)
        for index in range(3):
            Major.objects.create(
                name='رشته بزرگ %d' % index, slug='b%d' % index,
                degree='bachelor_cont', department=cls.big,
                group=big_group, is_active=True)
        Major.objects.create(
            name='رشته کوچک', slug='k1', degree='master',
            department=cls.small, group=small_group, is_active=True)

    def setUp(self):
        cache.clear()

    def _html(self):
        return self.client.get(reverse('academics:departments')).content.decode()

    def _bar(self):
        return self._html().split('trunk-bar')[1].split('</div>')[0]

    def test_each_faculty_gets_a_slice(self):
        self.assertEqual(self._bar().count('trunk-slice'), 2)

    def test_the_width_follows_the_major_count(self):
        """سه رشته در برابر یک رشته — سه برابر پهن‌تر."""
        bar = self._bar()
        self.assertIn('flex-grow:3', bar)
        self.assertIn('flex-grow:1', bar)

    def test_the_bar_is_described_for_screen_readers(self):
        """نموداری بدون توضیح، برای صفحه‌خوان هیچ است."""
        bar = self._bar()
        self.assertIn('role="img"', bar)
        self.assertIn('aria-label', bar)

    def test_the_key_states_each_share(self):
        key = self._html().split('trunk-key')[1].split('</ul>')[0]
        self.assertIn('75.0', key)
        self.assertIn('25.0', key)

    def test_the_key_jumps_to_its_faculty(self):
        key = self._html().split('trunk-key')[1].split('</ul>')[0]
        self.assertIn('href="#big"', key)
        self.assertIn('id="big"', self._html())

    def test_no_majors_does_not_divide_by_zero(self):
        Major.objects.all().delete()
        cache.clear()
        self.assertEqual(
            self.client.get(reverse('academics:departments')).status_code, 200)


class DegreeChipTests(TestCase):
    """هر گروه، مقطع‌هایی که واقعاً دارد."""

    @classmethod
    def setUpTestData(cls):
        cls.faculty = Department.objects.create(
            name='دانشکده فنی', slug='fanni', order=1, is_active=True)
        cls.group = AcademicGroup.objects.create(
            name='گروه کامپیوتر', slug='computer',
            department=cls.faculty, is_active=True)
        Major.objects.create(
            name='مهندسی کامپیوتر', slug='m1', degree='bachelor_cont',
            department=cls.faculty, group=cls.group, is_active=True)
        Major.objects.create(
            name='کاردانی کامپیوتر', slug='m2', degree='associate_cont',
            department=cls.faculty, group=cls.group, is_active=True)
        Major.objects.create(
            name='نرم‌افزار', slug='m3', degree='bachelor_cont',
            department=cls.faculty, group=cls.group, is_active=True)

    def setUp(self):
        cache.clear()

    def _summary(self):
        html = self.client.get(
            reverse('academics:departments')).content.decode()
        return html.split('<summary>')[1].split('</summary>')[0]

    def test_each_degree_is_named_once(self):
        """دو رشتهٔ کارشناسی نباید دو نشان یکسان بسازد."""
        self.assertEqual(self._summary().count('branch-degree"'), 2)

    def test_a_degree_the_group_lacks_is_not_offered(self):
        self.assertNotIn('کارشناسی ارشد', self._summary())

    def test_the_group_shows_how_many_majors_it_holds(self):
        self.assertIn('>3</span>', self._summary())


class ProgressiveEnhancementTests(TestCase):
    """صفحه باید بدون جاوااسکریپت کامل باشد."""

    @classmethod
    def setUpTestData(cls):
        faculty = Department.objects.create(
            name='دانشکده فنی', slug='fanni', order=1, is_active=True)
        group = AcademicGroup.objects.create(
            name='گروه کامپیوتر', slug='computer',
            department=faculty, is_active=True)
        Major.objects.create(
            name='مهندسی کامپیوتر', slug='m1', degree='bachelor_cont',
            department=faculty, group=group, is_active=True)

    def setUp(self):
        cache.clear()

    def _html(self):
        return self.client.get(reverse('academics:departments')).content.decode()

    def _js(self):
        return (Path(settings.BASE_DIR) / 'static' / 'js' / 'main.js').read_text(
            encoding='utf-8')

    def test_the_toolbar_stays_hidden_until_the_script_shows_it(self):
        """جعبهٔ جست‌وجویی که کار نمی‌کند، بدتر از نبودنش است."""
        tools = self._html().split('data-tree-tools')[1].split('>')[0]
        self.assertIn('hidden', tools)

    def test_the_script_reveals_it(self):
        js = self._js()
        self.assertIn('[data-tree-tools]', js)
        self.assertIn('tools.hidden = false', js)

    def test_the_filter_matches_arabic_spellings(self):
        """کسی که «مهندسي» می‌نویسد باید «مهندسی» را پیدا کند."""
        block = self._js().split('data-tree-tools')[1]
        self.assertIn('ي', block)
        self.assertIn('ك', block)
        self.assertIn('u200c', block)

    def test_every_major_is_searchable_from_the_markup(self):
        leaf = self._html().split('data-tree-leaf')[1].split('>')[0]
        self.assertIn('data-search=', leaf)
        self.assertIn('مهندسی کامپیوتر', leaf)

    def test_the_search_box_is_labelled(self):
        box = self._html().split('data-tree-filter')[1].split('>')[0]
        self.assertIn('aria-label', box)

    def test_the_result_count_announces_itself(self):
        tools = self._html().split('data-tree-count')[1].split('>')[0]
        self.assertIn('aria-live', tools)


class TrunkStyleTests(TestCase):
    """قواعدی که شکستنشان روی صفحه پیداست."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.css = (Path(settings.BASE_DIR) / 'static' / 'css' /
                   'main.css').read_text(encoding='utf-8')

    def _block(self):
        return self.css.split('درخت ساختار آموزشی')[1]

    def test_the_braces_balance(self):
        """یک آکولاد اضافه، همهٔ قواعد پس از خودش را بی‌اثر می‌کند."""
        depth = 0
        for number, line in enumerate(self.css.splitlines(), 1):
            depth += line.count('{') - line.count('}')
            self.assertGreaterEqual(depth, 0, 'آکولاد اضافه در خط %d' % number)
        self.assertEqual(depth, 0)

    def test_the_tree_uses_logical_properties(self):
        """صفحه راست‌چین است؛ left/right درخت را وارونه می‌کند."""
        block = self._block()
        for bad in ('margin-left:', 'margin-right:',
                    'padding-left:', 'padding-right:'):
            self.assertNotIn(bad, block, bad)

    def test_persian_text_is_never_letter_spaced(self):
        """letter-spacing حروف فارسی را از هم می‌کَند و کلمه را می‌شکند.

        فقط اعلان‌ها سنجیده می‌شوند، نه توضیحات — کامنتی که همین قید
        را شرح می‌دهد نباید خودش تخلف به‌حساب بیاید.
        """
        self.assertNotIn('letter-spacing:', self._block())

    def test_reduced_motion_is_respected(self):
        self.assertIn('prefers-reduced-motion', self._block())

    def test_the_dark_theme_is_designed_not_inherited(self):
        block = self._block()
        self.assertIn('[data-theme="dark"] .tone-1', block)
        self.assertIn('[data-theme="dark"] .branch summary', block)

    def test_counts_line_up(self):
        self.assertIn('tabular-nums', self._block())

    def test_keyboard_focus_is_visible(self):
        block = self._block()
        self.assertIn('.branch summary:focus-visible', block)
        self.assertIn('.leaf a:focus-visible', block)

    def test_the_tones_come_from_the_institute_palette(self):
        """رنگ تازه‌ای که با نشان موسسه بیگانه باشد وارد نشود."""
        block = self._block()
        self.assertIn('--tone: var(--primary', block)
        self.assertIn('--tone: var(--gold-ink', block)
