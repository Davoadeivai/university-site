"""منوی معاونت‌ها باید مو به مو با چارت سازمانی بخواند."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.vices import STATIC_UNITS, build

# آنچه در چارت سازمانی موسسه هست — عنوان و سطحش.
#
# این جدول عمداً دستی از روی تصویر نوشته شده، نه از روی کد؛ وگرنه
# آزمون فقط کد را با خودش می‌سنجید و هر اشتباهی را تأیید می‌کرد.
CHART = {
    'education': [
        ('کارگزینی هیئت علمی', []),
        ('حوزهٔ خدمات آموزشی', [
            ('مدیر آموزش', [
                'کارشناسان آموزشی', 'امور فارغ‌التحصیلان', 'ادارهٔ امتحانات']),
        ]),
        ('گروه‌های آموزشی', [('مدیریت گروه', ['اعضای هیئت علمی'])]),
    ],
    'research': [
        ('مدیر پژوهشی', [
            ('انتشارات', []), ('کتابخانه', []), ('دفتر ارتباط با صنعت', [])]),
        ('مدیر فناوری', [('مرکز کامپیوتر', [])]),
    ],
    'admin_finance': [
        ('مدیر امور مالی و خزانه‌دار', [
            ('رئیس حسابداری', []), ('حسابدار', []),
            ('کاربردی', []), ('حسابدار اموال', [])]),
        ('مدیر اداری و پشتیبانی', [
            ('کارگزینی و دبیرخانه', []), ('امور اداری و پشتیبانی', [])]),
    ],
    'student': [
        ('مدیر دانشجویی', [
            ('ادارهٔ بهداشت و وام دانشجویی', []),
            ('ادارهٔ خوابگاه‌ها و نظام وظیفه', []),
            ('ادارهٔ تربیت بدنی', [])]),
        ('مدیر فرهنگی', [('ادارهٔ فرهنگی و فوق‌برنامه', [])]),
        ('شورای فرهنگی', []),
        ('شورای دانشجویی', []),
        ('کمیته انضباطی', []),
    ],
}


def _titles(rows):
    return [row['title'] for row in rows]


def _find(rows, title):
    for row in rows:
        if row['title'] == title:
            return row
    return None


class ChartFidelityTests(TestCase):
    """هر جعبهٔ چارت باید در منو باشد، زیر همان والدِ خودش."""

    def setUp(self):
        cache.clear()
        self.rows = {row['key']: row for row in build()}

    def test_every_top_box_of_the_chart_is_a_menu_row(self):
        for key, boxes in CHART.items():
            children = self.rows[key]['children']
            for title, _kids in boxes:
                self.assertIsNotNone(
                    _find(children, title),
                    '«%s» زیر %s نیست' % (title, key))

    def test_every_second_level_box_sits_under_its_own_parent(self):
        for key, boxes in CHART.items():
            children = self.rows[key]['children']
            for title, kids in boxes:
                parent = _find(children, title)
                for kid in kids:
                    name = kid[0] if isinstance(kid, tuple) else kid
                    self.assertIsNotNone(
                        _find(parent['children'], name),
                        '«%s» زیر «%s» نیست' % (name, title))

    def test_every_third_level_box_is_there_too(self):
        """چارت سه سطح دارد؛ فهرست تخت آن را نشان نمی‌داد."""
        education = self.rows['education']['children']
        services = _find(education, 'حوزهٔ خدمات آموزشی')
        manager = _find(services['children'], 'مدیر آموزش')
        self.assertEqual(
            sorted(_titles(manager['children'])),
            sorted(['کارشناسان آموزشی', 'امور فارغ‌التحصیلان',
                    'ادارهٔ امتحانات']))

    def test_the_order_within_each_deputy_follows_the_chart(self):
        for key, boxes in CHART.items():
            wanted = [title for title, _ in boxes]
            present = [t for t in _titles(self.rows[key]['children'])
                       if t in wanted]
            self.assertEqual(present, wanted, key)

    def test_nothing_extra_was_invented_under_a_deputy(self):
        """هر ردیفی که در چارت نیست، باید دلیلی داشته باشد."""
        allowed_extra = {
            'education': {'تحصیلات تکمیلی'},
            'research': {'دفتر همکاری‌های علمی و بین‌المللی',
                         'منابع پژوهشی'},
            'admin_finance': set(),
            'student': set(),
        }
        for key, boxes in CHART.items():
            chart_names = {title for title, _ in boxes}
            present = set(_titles(self.rows[key]['children']))
            surprise = present - chart_names - allowed_extra[key]
            self.assertEqual(surprise, set(), key)


class ChartInTheMenuTests(TestCase):
    """آنچه ساخته شد باید روی صفحه هم دیده شود."""

    def setUp(self):
        cache.clear()

    def _nav(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="mainNav"')[1].split('</nav>')[0]

    def test_the_deep_boxes_reach_the_page(self):
        nav = self._nav()
        for title in ('کارشناسان آموزشی', 'حسابدار اموال',
                      'ادارهٔ تربیت بدنی', 'مرکز کامپیوتر',
                      'کارگزینی و دبیرخانه'):
            self.assertIn(title, nav, title)

    def test_the_third_level_is_nested_not_flattened(self):
        self.assertIn('vice-sub-deep', self._nav())

    def test_a_box_without_a_page_is_plain_text(self):
        """لینکی که به ۴۰۴ برسد بدتر از نبودن لینک است."""
        nav = self._nav()
        block = nav.split('کارشناسان آموزشی')[0][-160:]
        self.assertIn('is-plain', block)

    def test_a_box_that_has_a_page_is_a_link(self):
        nav = self._nav()
        self.assertIn(reverse('academics:groups_list'), nav)
        self.assertIn(reverse('library:library'), nav)

    def test_the_deputy_itself_is_still_reachable(self):
        from core.vices import VICE_ORDER

        nav = self._nav()
        for key, _label, _icon in VICE_ORDER:
            self.assertIn(reverse('core:vice_detail', args=[key]), nav)


class ChartConflictTests(TestCase):
    """جایی که چارت و سند اصلاحات با هم نمی‌خوانند."""

    def test_the_fifth_deputy_is_kept_but_left_empty(self):
        """چارت معاونت فنی و عمرانی ندارد؛ سند اصلاحات دارد.

        حذفش تصمیم موسسه است، نه من: در فهرست می‌ماند و زیرمجموعه‌ای
        برایش ساخته نشده تا چیزی از خودم به چارت اضافه نکرده باشم.
        """
        self.assertIn('construction', STATIC_UNITS)
        self.assertEqual(STATIC_UNITS['construction'], [])
