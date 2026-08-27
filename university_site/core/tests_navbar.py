"""نوار بالای سایت و صفحهٔ معاونت‌ها — یک ساختار، دو نمایش.

ترتیب و زیرمجموعه‌ها از `core/vices.py` می‌آیند. پیش از این منو در
قالب دستی نوشته شده بود و صفحه جداگانه از دیتابیس می‌خواند؛ دو
منبع برای یک چیز، که دیر یا زود با هم اختلاف پیدا می‌کنند.
"""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import VicePresidency
from core.vices import VICE_ORDER, build


class VicesStructureTests(TestCase):
    """خودِ ساختار، بدون قالب."""

    def test_the_document_order_is_kept(self):
        keys = [row['key'] for row in build({})]
        self.assertEqual(keys, ['education', 'research', 'admin_finance',
                                'student', 'construction'])

    def test_numbering_starts_at_one(self):
        rows = build({})
        self.assertEqual([r['number'] for r in rows], [1, 2, 3, 4, 5])

    def test_a_missing_record_still_appears(self):
        """معاونتی که ردیف ندارد نباید از منو حذف شود.

        صفحه‌اش خودش می‌گوید اطلاعاتش پر نشده؛ نبودنش در منو فقط
        بازدیدکننده را سردرگم می‌کند.
        """
        rows = build({})
        self.assertEqual(len(rows), len(VICE_ORDER))
        self.assertTrue(all(row['vice'] is None for row in rows))

    def test_graduate_studies_sits_under_education(self):
        row = build({})[0]
        titles = [child['title'] for child in row['children']]
        self.assertIn('تحصیلات تکمیلی', titles)

    def test_the_international_office_sits_under_research(self):
        row = build({})[1]
        titles = [child['title'] for child in row['children']]
        self.assertIn('دفتر همکاری‌های علمی و بین‌المللی', titles)

    def test_admin_units_are_appended(self):
        vice = VicePresidency.objects.create(
            vice_type='student', full_name='دکتر تست', is_active=True)
        vice.units.create(name='ادارهٔ رفاه', is_active=True)
        rows = build({'student': vice})
        student = [r for r in rows if r['key'] == 'student'][0]
        self.assertIn('ادارهٔ رفاه',
                      [c['title'] for c in student['children']])

    def test_an_inactive_unit_is_skipped(self):
        vice = VicePresidency.objects.create(
            vice_type='student', full_name='دکتر تست', is_active=True)
        vice.units.create(name='واحد بسته', is_active=False)
        rows = build({'student': vice})
        student = [r for r in rows if r['key'] == 'student'][0]
        self.assertNotIn('واحد بسته',
                         [c['title'] for c in student['children']])

    def test_every_row_has_a_url(self):
        self.assertTrue(all(row['url'] for row in build({})))


class DeputiesMenuTests(TestCase):
    """منوی «معاونت‌ها» در نوار بالا."""

    @classmethod
    def setUpTestData(cls):
        VicePresidency.objects.create(
            vice_type='education', full_name='دکتر محمدعلی جعفری',
            is_active=True)
        VicePresidency.objects.create(
            vice_type='research', full_name='دکتر حسن عمرانی',
            is_active=True)

    def setUp(self):
        # context_processor فهرست را ۶۰ ثانیه کش می‌کند
        cache.clear()

    def _nav(self):
        """کل منوی معاونت‌ها، با زیرمنوهای تودرتویش.

        بریدن تا اولین ‎</ul>‎ دیگر کار نمی‌کند: هر معاونت زیرمنوی
        خودش را دارد و آن زودتر بسته می‌شود، پس منو از معاونت دوم
        به بعد بریده می‌شد.
        """
        html = self.client.get(reverse('core:home')).content.decode()
        rest = html.split('nav-dd-vices')[1]
        depth = 1
        cursor = 0
        while depth and cursor < len(rest):
            opening = rest.find('<ul', cursor)
            closing = rest.find('</ul>', cursor)
            if closing < 0:
                break
            if 0 <= opening < closing:
                depth += 1
                cursor = opening + 3
            else:
                depth -= 1
                cursor = closing + 5
        return rest[:cursor]

    def test_the_menu_is_called_deputyships(self):
        """موسسه خواست «معاونین» به «معاونت‌ها» تغییر کند."""
        html = self.client.get(reverse('core:home')).content.decode()
        head = html.split('fa-users-cog')[1][:120]
        self.assertIn('معاونت‌ها', head)
        self.assertNotIn('معاونین', head)

    def test_the_catch_all_item_is_gone(self):
        """عنوان منو خودش به همان صفحه می‌رود؛ تکرارش ردیف اضافه بود."""
        self.assertNotIn('همهٔ معاونین', self._nav())

    def test_the_menu_title_still_reaches_the_page(self):
        html = self.client.get(reverse('core:home')).content.decode()
        toggle = html.split('fa-users-cog')[0][-200:]
        self.assertIn(reverse('core:vices_list'), toggle)

    def test_each_deputy_is_listed_once_and_numbered(self):
        nav = self._nav()
        for number, (key, _label, _icon) in enumerate(VICE_ORDER, start=1):
            url = reverse('core:vice_detail', args=[key])
            self.assertEqual(nav.count('href="%s"' % url), 1,
                             '%s یک بار در منو نیست' % key)
        for number in range(1, 6):
            self.assertIn('>%d</span>' % number, nav,
                          'شمارهٔ %d در منو نیست' % number)

    def test_deputies_left_the_presidency_menu(self):
        html = self.client.get(reverse('core:home')).content.decode()
        presidency = html.split('fa-user-tie')[1].split('</ul>')[0]
        self.assertNotIn(reverse('core:vice_detail', args=['education']),
                         presidency)

    def test_the_menu_survives_an_empty_database(self):
        VicePresidency.objects.all().delete()
        cache.clear()
        nav = self._nav()
        self.assertIn('معاونت آموزشی', nav)
        self.assertIn('معاونت فنی و عمرانی', nav)


class VicesPageTests(TestCase):
    """صفحهٔ معاونت‌ها — همان ساختار، نمایش دیگر."""

    @classmethod
    def setUpTestData(cls):
        vice = VicePresidency.objects.create(
            vice_type='education', full_name='دکتر محمدعلی جعفری',
            academic_rank='دانشیار', email='edu@aab.ac.ir',
            description='شرح فعالیت معاونت آموزشی.', is_active=True)
        vice.units.create(name='ادارهٔ آموزش', is_active=True)

    def setUp(self):
        cache.clear()

    def _html(self):
        return self.client.get(reverse('core:vices_list')).content.decode()

    def test_the_page_opens(self):
        self.assertEqual(
            self.client.get(reverse('core:vices_list')).status_code, 200)

    def test_all_five_are_shown_in_order(self):
        html = self._html()
        positions = [html.index(label) for _key, label, _icon in VICE_ORDER]
        self.assertEqual(positions, sorted(positions),
                         'ترتیب صفحه با ترتیب سند یکی نیست')

    def test_the_person_and_the_office_are_merged(self):
        """موسسه خواست «معاونین» و «معاونت‌ها» یک چیز شوند."""
        html = self._html()
        self.assertIn('معاونت آموزشی', html)
        self.assertIn('دکتر محمدعلی جعفری', html)
        self.assertIn('دانشیار', html)

    def test_units_appear_under_their_deputy(self):
        """فقط بدنهٔ صفحه سنجیده می‌شود، نه نوار بالا.

        پیش از این جست‌وجو از اولین «معاونت آموزشی» شروع می‌شد و آن
        در منوی بالای سایت بود، نه در صفحه — یعنی این آزمون چیزی را
        که ادعا می‌کرد نمی‌سنجید.
        """
        html = self._html().split('<main')[1]
        # از کارت معاونت آموزشی تا کارت بعدی — نشانهٔ شروع هر کارت،
        # شمارهٔ روی ستون است، نه نام کلاسی که جای دیگری هم بیاید.
        # maxsplit=1 لازم است: «معاونت آموزشی» در شرح خودِ معاونت هم
        # تکرار شده، و بدون آن، بلوک همان‌جا بریده می‌شد — پیش از
        # رسیدن به زیرمجموعه‌ها.
        block = html.split('معاونت آموزشی', 1)[1].split('vice-marker')[0]
        self.assertIn('ادارهٔ آموزش', block)

    def test_a_missing_record_is_reported_to_staff_only(self):
        """بازدیدکننده لازم نیست بداند کدام رکورد پر نشده.

        ادمین باید بداند چه مانده، ولی نوشتنش برای عموم فقط ناتمامیِ
        سایت را جار می‌زند.
        """
        from django.contrib.auth.models import User

        self.assertNotIn('هنوز ثبت نشده', self._html())

        User.objects.create_user('kar3', password='Str0ng!Pass2026',
                                 is_staff=True)
        self.client.login(username='kar3', password='Str0ng!Pass2026')
        cache.clear()
        self.assertIn('هنوز ثبت نشده', self._html())

    def test_the_numbers_are_shown(self):
        html = self._html()
        for number in range(1, 6):
            self.assertIn('vice-marker" aria-hidden="true">%d<' % number, html)

    def test_the_page_and_the_menu_agree(self):
        """هر دو از یک منبع می‌خوانند؛ این تست همان را قفل می‌کند."""
        page = self._html()
        home = self.client.get(reverse('core:home')).content.decode()
        for key, _label, _icon in VICE_ORDER:
            url = reverse('core:vice_detail', args=[key])
            self.assertIn(url, page)
            self.assertIn(url, home)
