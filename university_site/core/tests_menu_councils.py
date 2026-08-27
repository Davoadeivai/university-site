"""منو: گالری به فوتر، معاونت‌ها تودرتو، و آیتم شوراها."""
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import Council


class GalleryMovedToFooterTests(TestCase):
    """گالری از نوار بالا برداشته شد؛ تنها راهش فوتر است."""

    def setUp(self):
        cache.clear()

    def _page(self):
        return self.client.get(reverse('core:home')).content.decode()

    def _nav(self):
        return self._page().split('id="mainNav"')[1].split('</nav>')[0]

    def _footer(self):
        return self._page().split('</nav>')[-1]

    def test_it_is_gone_from_the_navbar(self):
        self.assertNotIn('گالری تصاویر', self._nav())

    def test_it_is_reachable_from_the_footer(self):
        footer = self._footer()
        self.assertIn('گالری تصاویر', footer)
        self.assertIn(reverse('core:gallery'), footer)

    def test_the_gallery_page_still_works(self):
        self.assertEqual(
            self.client.get(reverse('core:gallery')).status_code, 200)

    def test_admin_links_do_not_push_the_gallery_out(self):
        """اگر مدیر «دسترسی سریع» را پر کند، گالری نباید گم شود."""
        from core.models import QuickLink

        for index in range(4):
            QuickLink.objects.create(
                title='لینک %d' % index, url='https://example.org/%d' % index,
                category='quick_access', is_active=True)
        cache.clear()
        footer = self._footer()
        self.assertIn('لینک 0', footer)
        self.assertIn('گالری تصاویر', footer)


class CouncilMenuTests(TestCase):
    """آیتم شوراها، میان معاونت‌ها و دانشکده‌ها."""

    def setUp(self):
        cache.clear()
        names = ('شورای موسسه', 'شورای فرهنگی', 'کمیته انضباطی')
        for index, name in enumerate(names, start=1):
            Council.objects.create(
                name=name, slug='c%d' % index, order=index, is_active=True)

    def _nav(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="mainNav"')[1].split('</nav>')[0]

    def test_the_item_exists(self):
        nav = self._nav()
        self.assertIn('شوراها', nav)
        self.assertIn(reverse('core:councils'), nav)

    def test_it_sits_between_deputies_and_faculties(self):
        nav = self._nav()
        deputies = nav.index('fa-users-cog')
        councils = nav.index(reverse('core:councils'))
        faculties = nav.index(reverse('academics:departments'))
        self.assertLess(deputies, councils)
        self.assertLess(councils, faculties)

    def test_each_council_is_listed(self):
        nav = self._nav()
        for name in ('شورای موسسه', 'شورای فرهنگی', 'کمیته انضباطی'):
            self.assertIn(name, nav)

    def test_an_inactive_council_is_left_out(self):
        Council.objects.filter(slug='c2').update(is_active=False)
        cache.clear()
        self.assertNotIn('شورای فرهنگی', self._nav())

    def test_no_councils_still_leaves_a_usable_item(self):
        Council.objects.all().delete()
        cache.clear()
        nav = self._nav()
        self.assertIn(reverse('core:councils'), nav)
        self.assertIn('فهرست شوراها', nav)


class CouncilPageTests(TestCase):
    """صفحهٔ شوراها و صفحهٔ هر شورا."""

    def setUp(self):
        cache.clear()
        self.council = Council.objects.create(
            name='شورای موسسه', slug='shora', order=1, is_active=True,
            short_description='بالاترین رکن تصمیم‌گیری.',
            head='دکتر حسن فارسیجانی',
            duties='تصویب بودجه\nنظارت بر مصوبات',
            members='دکتر الف — رئیس\nدکتر ب — دبیر')

    def test_the_list_opens(self):
        self.assertEqual(
            self.client.get(reverse('core:councils')).status_code, 200)

    def test_the_list_shows_each_council(self):
        html = self.client.get(reverse('core:councils')).content.decode()
        self.assertIn('شورای موسسه', html)
        self.assertIn('بالاترین رکن تصمیم‌گیری.', html)

    def test_the_detail_opens(self):
        self.assertEqual(
            self.client.get(self.council.get_absolute_url()).status_code, 200)

    def test_duties_are_split_by_line(self):
        html = self.client.get(self.council.get_absolute_url()).content.decode()
        block = html.split('council-duties')[1].split('</ul>')[0]
        self.assertEqual(block.count('<li>'), 2)

    def test_members_are_split_by_line(self):
        html = self.client.get(self.council.get_absolute_url()).content.decode()
        block = html.split('council-members')[1].split('</ul>')[0]
        self.assertIn('دکتر الف', block)

    def test_an_empty_council_says_so_instead_of_showing_nothing(self):
        bare = Council.objects.create(
            name='شورای خالی', slug='khali', order=2, is_active=True)
        html = self.client.get(bare.get_absolute_url()).content.decode()
        self.assertIn('هنوز ثبت نشده', html)

    def test_an_inactive_council_is_not_reachable(self):
        self.council.is_active = False
        self.council.save(update_fields=['is_active'])
        self.assertEqual(
            self.client.get(self.council.get_absolute_url()).status_code, 404)

    def test_the_breadcrumb_leads_back(self):
        html = self.client.get(self.council.get_absolute_url()).content.decode()
        crumbs = html.split('<ol class="breadcrumb">')[1].split('</ol>')[0]
        self.assertIn(reverse('core:councils'), crumbs)

    def test_the_seeder_records_the_chart_councils(self):
        from io import StringIO

        from django.core.management import call_command

        Council.objects.all().delete()
        call_command('seed_councils', stdout=StringIO())
        names = set(Council.objects.values_list('name', flat=True))
        self.assertEqual(names, {'شورای موسسه', 'شورای فرهنگی',
                                 'شورای دانشجویی', 'کمیته انضباطی'})

    def test_the_seeder_does_not_overwrite_edits(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_councils', stdout=StringIO())
        target = Council.objects.get(slug='shoraye-farhangi')
        target.short_description = 'متن دست‌نویس مدیر'
        target.save(update_fields=['short_description'])
        call_command('seed_councils', stdout=StringIO())
        target.refresh_from_db()
        self.assertEqual(target.short_description, 'متن دست‌نویس مدیر')


class NestedDeputyMenuTests(TestCase):
    """زیرشاخه‌های پنج معاونت با هم باز بودند و منو سی‌ردیفه می‌شد."""

    def setUp(self):
        cache.clear()

    def _nav(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="mainNav"')[1].split('</nav>')[0]

    def test_children_sit_in_their_own_list(self):
        self.assertIn('vice-sub', self._nav())

    def test_each_deputy_with_children_gets_a_toggle(self):
        nav = self._nav()
        self.assertEqual(nav.count('vice-toggle'),
                         nav.count('<ul class="vice-sub">'))

    def test_the_toggle_says_whether_it_is_open(self):
        self.assertIn('aria-expanded="false"', self._nav())

    def test_the_toggle_is_labelled(self):
        """دکمه‌ای که فقط یک فلش است، برای صفحه‌خوان بی‌نام است."""
        self.assertIn('aria-label="زیرشاخه‌های', self._nav())

    def test_the_deputy_name_is_still_a_link(self):
        """بدون جاوااسکریپت هم باید به صفحهٔ هر معاونت رسید."""
        from core.vices import VICE_ORDER

        nav = self._nav()
        for key, _label, _icon in VICE_ORDER:
            self.assertIn(reverse('core:vice_detail', args=[key]), nav)

    def test_the_script_does_not_close_the_parent_menu(self):
        js = (Path(settings.BASE_DIR) / 'static' / 'js' / 'main.js').read_text(
            encoding='utf-8')
        self.assertIn('.vice-toggle', js)
        self.assertIn('stopPropagation', js)

    def test_the_submenu_opens_towards_the_left(self):
        """موسسه خواست کشویی از سمت چپ باز شود.

        در صفحهٔ راست‌چین، inline-start همان «راست» است؛ پس
        ‎inset-inline-start: 100%‎ لبهٔ راستِ زیرمنو را به لبهٔ چپِ منو
        می‌چسباند و زیرمنو به چپ باز می‌شود. مقدار ‎inline-end‎ دقیقاً
        برعکسش را می‌کند و یک بار همین اشتباه رخ داد.
        """
        css = (Path(settings.BASE_DIR) / 'static' / 'css' /
               'main.css').read_text(encoding='utf-8')
        # قاعدهٔ دسکتاپ، نه قاعدهٔ پایه: اولین ‎.vice-sub‎ در فایل فقط
        # فهرست را صاف می‌کند و جای‌گذاری در بلوک ‎min-width: 992px‎ است.
        desktop = css.split('.vice-group.has-sub { position: relative; }')[1]
        block = desktop.split('.vice-sub {')[1].split('}')[0]
        self.assertIn('inset-inline-start: 100%', block)
        self.assertNotIn('inset-inline-end', block)

    def test_the_arrow_points_the_way_the_menu_opens(self):
        """فلشی که به راست اشاره کند و منو به چپ باز شود، دروغ است."""
        html = self.client.get(reverse('core:home')).content.decode()
        nav = html.split('id="mainNav"')[1].split('</nav>')[0]
        toggle = nav.split('vice-toggle')[1].split('</button>')[0]
        self.assertIn('fa-chevron-left', toggle)

    def test_the_submenu_has_its_own_ground(self):
        """اگر زیرمنو و منو یک رنگ باشند، لایهٔ تازه دیده نمی‌شود."""
        css = (Path(settings.BASE_DIR) / 'static' / 'css' /
               'main.css').read_text(encoding='utf-8')
        desktop = css.split('.vice-group.has-sub { position: relative; }')[1]
        block = desktop.split('.vice-sub {')[1].split('}')[0]
        self.assertIn('background: var(--primary,', block)
        # فقط اعلان background سنجیده می‌شود، نه کامنتی که تاریخچهٔ
        # همین تغییر را شرح می‌دهد و خودش نام رنگ قدیمی را می‌برد.
        declared = [line.strip() for line in block.splitlines()
                    if line.strip().startswith('background:')]
        self.assertEqual(len(declared), 1)
        self.assertNotIn('--primary-deep', declared[0])

    def test_the_submenu_rows_use_the_institute_palette(self):
        """‎#b8cce4‎ از تم سرمه‌ای قدیمی مانده بود و بیگانه بود."""
        css = (Path(settings.BASE_DIR) / 'static' / 'css' /
               'main.css').read_text(encoding='utf-8')
        block = css.split('.vice-sub .nav-dd-sub {')[1].split('}')[0]
        self.assertIn('--bnr-gold-300', block)
        self.assertNotIn('#b8cce4', block)

    def test_hovering_a_submenu_row_is_visible(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'css' /
               'main.css').read_text(encoding='utf-8')
        self.assertIn('.vice-sub .nav-dd-sub:hover', css)

    def test_desktop_opens_on_focus_not_only_hover(self):
        """کاربر صفحه‌کلید با هاورِ تنها هیچ‌وقت به زیرشاخه نمی‌رسد."""
        css = (Path(settings.BASE_DIR) / 'static' / 'css' /
               'main.css').read_text(encoding='utf-8')
        self.assertIn('.vice-group.has-sub:focus-within > .vice-sub', css)
