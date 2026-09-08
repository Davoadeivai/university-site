"""منوی معاونت‌ها: تب فعال، و زیرمنویی که زیر دست نمی‌پرد."""
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import VicePresidency


def _css():
    return (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
        encoding='utf-8')


def _desktop_block():
    css = _css()
    start = css.index('/* ── دسکتاپ: زیرمنو از کنار باز می‌شود ── */')
    return css[start:start + 4000]


class TheTabKnowsWhereYouAreTests(TestCase):
    """تا امروز فقط «صفحه اصلی» فعال می‌شد و بقیه هیچ‌وقت."""

    def setUp(self):
        cache.clear()
        VicePresidency.objects.create(vice_type='education', is_active=True)

    def _tab(self, page, tab_href):
        """تگِ همان لینکِ نوار بالا که به این نشانی می‌رود."""
        cache.clear()
        html = self.client.get(page).content.decode()
        for chunk in html.split('<a class="nav-link-flat')[1:]:
            tag = chunk.split('>')[0]
            if 'href="%s"' % tab_href in tag:
                return tag
        self.fail('لینک %s در نوار بالا نیست' % tab_href)

    def test_the_vices_tab_lights_up_on_its_own_page(self):
        url = reverse('core:vices_list')
        self.assertIn('active', self._tab(url, url))

    def test_it_stays_lit_inside_a_single_vice(self):
        tag = self._tab(reverse('core:vice_detail', args=['education']),
                        reverse('core:vices_list'))
        self.assertIn('active', tag)

    def test_it_is_dark_on_an_unrelated_page(self):
        tag = self._tab(reverse('core:councils'),
                        reverse('core:vices_list'))
        self.assertNotIn('active', tag)

    def test_another_tab_lights_up_instead(self):
        url = reverse('core:councils')
        self.assertIn('active', self._tab(url, url))

    def test_the_home_tab_still_works(self):
        url = reverse('core:home')
        self.assertIn('active', self._tab(url, url))


class TheActiveTabMapTests(TestCase):

    def _tab(self, url):
        from django.urls import resolve

        from core.context_processors import _active_tab

        class _Request:
            resolver_match = None

        # نشانی‌های فارسی درصدی کدگذاری می‌شوند و resolve خام می‌خواهد
        from urllib.parse import unquote

        request = _Request()
        request.resolver_match = resolve(unquote(url))
        return _active_tab(request)

    def test_a_vice_page_belongs_to_the_vices_tab(self):
        self.assertEqual(self._tab(reverse('core:vices_list')), 'vices')
        self.assertEqual(
            self._tab(reverse('core:vice_detail', args=['research'])), 'vices')

    def test_graduate_studies_sits_under_the_vices_tab(self):
        """در چارت، تحصیلات تکمیلی زیر معاونت آموزشی است."""
        self.assertEqual(self._tab(reverse('core:graduate_studies')), 'vices')

    def test_a_whole_namespace_can_map_at_once(self):
        self.assertEqual(self._tab(reverse('news:list')), 'news')

    def test_an_unmapped_page_lights_nothing(self):
        self.assertEqual(self._tab(reverse('core:search')), '')

    def test_a_request_without_a_match_is_harmless(self):
        from core.context_processors import _active_tab

        class _Bare:
            pass

        self.assertEqual(_active_tab(_Bare()), '')


class TheSubmenuOpensInPlaceTests(TestCase):
    """پنجرهٔ کنارى رفت؛ زیرشاخه در همان ستون باز می‌شود.

    برای رسیدن به آن پنجره باید از روی ردیف‌های میانی رد می‌شدی و هر
    کدام زیرمنوی خودش را باز می‌کرد — منو زیر دست می‌پرید. حالا سفرِ
    موربی در کار نیست.
    """

    def _accordion(self):
        """قاعده‌ای که زیرمنو را جمع و باز می‌کند.

        دو قاعده با همین انتخابگر هست — یکی پایهٔ فهرست، یکی رفتار —
        پس همان که جمع‌شدن دارد برداشته می‌شود، نه اولی.
        """
        css = _css()
        start = css.index('max-block-size: 0;')
        return css[css.rindex('.vice-sub {', 0, start):
                   css.index('}', start)]

    def test_the_flyout_is_gone(self):
        css = _css()
        self.assertNotIn('.vice-group.has-sub:hover > .vice-sub', css)
        self.assertNotIn('inset-inline-start: 100%', self._accordion())

    def test_it_expands_where_it_stands(self):
        rule = self._accordion()
        self.assertIn('max-block-size: 0', rule)
        self.assertIn('overflow: hidden', rule)

    def test_every_row_keeps_its_own_line(self):
        """با ‎grid-template-rows‎ همهٔ ردیف‌ها در یک ردیف می‌نشستند و
        نام رشته روی مقطعش می‌افتاد؛ گرید یک فرزند می‌خواهد."""
        import re

        # توضیحِ خودِ قاعده اسمِ ترفندِ قبلی را می‌برد؛ اعلان‌ها مهم‌اند
        rule = re.sub(r'/\*.*?\*/', '', self._accordion(), flags=re.S)
        self.assertIn('display: block', rule)
        self.assertNotIn('grid-template-rows', rule)

    def test_opening_is_animated_not_a_jump(self):
        self.assertIn('transition: max-block-size', self._accordion())

    def test_only_an_opened_branch_is_shown(self):
        css = _css()
        self.assertIn('.vice-group.has-sub.is-open > .vice-sub', css)
        block = css[css.index('.vice-group.has-sub.is-open > .vice-sub'):][:400]
        self.assertIn('max-block-size: 160vh', block)

    def test_keyboard_focus_opens_it_too(self):
        """بدون این، کسی که با Tab می‌گردد هیچ‌وقت زیرشاخه را نمی‌بیند."""
        self.assertIn('.vice-group.has-sub:focus-within > .vice-sub', _css())

    def test_the_arrow_button_works_everywhere_now(self):
        """پیش از این روی دسکتاپ pointer-events نداشت."""
        css = _css()
        toggle = css[css.index(chr(10) + '.vice-toggle {'):][:400]
        self.assertNotIn('pointer-events: none', toggle)

    def test_someone_who_dislikes_motion_gets_no_animation(self):
        css = _css()
        self.assertIn('.vice-sub { transition: none; }', css)


class EachBranchKeepsItsOwnColourTests(TestCase):
    """پنج معاونت، پنج رنگ — و زیرمجموعه هم‌رنگِ رکنِ خودش."""

    def test_the_open_branch_is_tinted_by_its_vice(self):
        css = _css()
        block = css[css.index('.vice-group.has-sub > .vice-sub {'):][:400]
        self.assertIn('var(--hue', block)
        self.assertIn('border-inline-start', block)

    def test_every_vice_has_a_hue_of_its_own(self):
        css = _css()
        hues = {css[css.index('.vice-hue-%d {' % n):][:90] for n in range(1, 6)}
        self.assertEqual(len(hues), 5)

    def test_the_third_level_reads_as_deeper(self):
        css = _css()
        block = css[css.index('.vice-sub .vice-sub {'):][:260]
        self.assertIn('margin-inline-start', block)
        self.assertIn('dashed', block)


class TheMenuStillWorksWithoutHoverTests(TestCase):
    """موبایل هاور ندارد؛ دکمهٔ فلش باید بماند."""

    def setUp(self):
        cache.clear()
        VicePresidency.objects.create(vice_type='student', is_active=True)

    def test_every_vice_with_children_has_a_toggle(self):
        html = self.client.get(reverse('core:home')).content.decode()
        menu = html.split('nav-dd-vices')[1].split('</ul>')[0]
        self.assertIn('vice-toggle', menu)

    def test_the_vice_name_is_always_a_link(self):
        html = self.client.get(reverse('core:home')).content.decode()
        menu = html.split('nav-dd-vices')[1]
        self.assertIn('vice-lead', menu)
        self.assertIn(reverse('core:vice_detail', args=['education']), menu)


class TheMenuFitsOnOneScreenTests(TestCase):
    """یک ستونِ بلند بود و برای دیدن معاونت پنجم باید تا ته اسکرول می‌کردی."""

    def _panel(self):
        """قاعدهٔ ستونی، نه قاعدهٔ پایهٔ کشویی که بالاتر در فایل است."""
        css = _css()
        start = css.index('grid-template-columns: repeat(var(--cols)')
        return css[css.rindex('.nav-dd-vices {', 0, start):
                   css.index('}', start)]

    def test_the_panel_lays_the_vices_side_by_side(self):
        self.assertIn('grid-template-columns: repeat(var(--cols)',
                      self._panel())

    def test_it_is_only_a_grid_once_it_is_open(self):
        """‎display‎ روی حالتِ بسته، پنل را همیشه روی صفحه نگه می‌داشت."""
        block = self._panel()
        self.assertNotIn('display:', block)
        css = _css()
        self.assertIn(
            '#mainNav .nav-item.has-mega > .dropdown-menu.nav-dd-vices.show',
            css)
        opened = css[css.index(
            '#mainNav .nav-item.has-mega:hover > .dropdown-menu.nav-dd-vices'):]
        self.assertIn('display: grid !important', opened[:520])

    def test_there_is_a_column_for_each_vice(self):
        self.assertIn('--cols: 5', self._panel())

    def test_the_faculties_menu_gets_its_own_count(self):
        """سه دانشکده در پنج ستون، دو ستون خالی می‌ماند."""
        self.assertIn(
            '#mainNav .nav-item.has-mega > .dropdown-menu.nav-dd-faculties',
            _css())

    def test_a_narrow_screen_gets_fewer_columns(self):
        css = _css()
        self.assertIn('@media (min-width: 1200px) and (max-width: 1400px)',
                      css)

    def test_the_panel_spans_the_whole_navbar(self):
        """پنلِ پهن که به آیتم بچسبد، روی همسایه‌هایش می‌افتد."""
        block = self._panel()
        self.assertIn('position: absolute', block)
        self.assertIn('inset-inline: 0', block)
        self.assertIn('inline-size: auto', block)

    def test_the_navbar_is_what_it_is_measured_against(self):
        css = _css()
        self.assertIn('#mainNav { position: relative; }', css)
        self.assertIn('#mainNav .nav-item.has-mega { position: static; }', css)

    def test_only_the_column_menus_are_detached(self):
        """بقیهٔ کشویی‌ها باید سرِ جای دکمهٔ خودشان بمانند."""
        html = self.client.get(reverse('core:home')).content.decode()
        nav = html.split('id="mainNav"')[1].split('</nav>')[0]
        self.assertEqual(nav.count('nav-item dropdown has-mega'), 2)

    def test_nothing_needs_opening_on_a_desktop(self):
        """در حالت ستونی، همه‌چیز از نگاه اول پیداست."""
        css = _css()
        block = css[css.index('.nav-dd-vices > .vice-group > .vice-sub {'):][:300]
        self.assertIn('max-block-size: none', block)
        self.assertIn('opacity: 1', block)

    def test_a_long_faculty_column_scrolls_by_itself(self):
        """چهل‌ویک رشته در سه ستون، بلندتر از قدِ صفحه است."""
        css = _css()
        block = css[css.index(
            '.nav-dd-faculties > .vice-group > .vice-sub {'):][:220]
        self.assertIn('max-block-size', block)
        self.assertIn('overflow-y: auto', block)

    def test_the_arrow_button_steps_aside_there(self):
        css = _css()
        self.assertIn(
            '.nav-dd-vices > .vice-group > .vice-lead-row .vice-toggle', css)

    def test_a_runaway_panel_still_cannot_leave_the_screen(self):
        block = self._panel()
        self.assertIn('max-block-size', block)
        self.assertIn('overflow-y: auto', block)

    def test_the_columns_wait_for_the_navbar_to_go_horizontal(self):
        """نوار با ‎navbar-expand-xl‎ تا ۱۲۰۰ پیکسل عمودی است.

        با شکستِ ۹۹۲، میان ۹۹۲ تا ۱۱۹۹ منوی عمودی ستون‌بندی می‌شد و
        پنلِ پهن روی بقیه می‌افتاد.
        """
        css = _css()
        mega = css.index('grid-template-columns: repeat(var(--cols)')
        guard = css.rindex('@media (min-width: ', 0, mega)
        self.assertIn('1200px', css[guard:guard + 40])

    def test_one_menu_at_a_time(self):
        """پنل تمام‌پهنا روی همسایه می‌افتد؛ دو منوی باز یعنی قاطی."""
        from pathlib import Path

        from django.conf import settings

        js = (Path(settings.BASE_DIR) / 'static' / 'js' /
              'main.js').read_text(encoding='utf-8')
        self.assertIn('items.forEach(function (other) {', js)
        self.assertIn('if (other !== item) { close(other); }', js)

    def test_clicking_a_destination_closes_the_menu(self):
        from pathlib import Path

        from django.conf import settings

        js = (Path(settings.BASE_DIR) / 'static' / 'js' /
              'main.js').read_text(encoding='utf-8')
        self.assertIn("event.target.closest('a[href]')", js)
