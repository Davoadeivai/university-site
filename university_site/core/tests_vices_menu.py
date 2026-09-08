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
        block = css[css.index(
            chr(10) + '.vice-group.has-sub.is-open > .vice-sub'):][:400]
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


class TheMenuLooksLikeEveryOtherOneTests(TestCase):
    """یک بار پنج‌ستونی و تمام‌پهنا شد؛ موسسه یک‌شکلی را خواست.

    بلند نبودنش از بسته‌بودنِ شاخه‌ها می‌آید، نه از پهن‌بودن پنل: در
    حالت بسته فقط پنج ردیفِ نام معاونت دیده می‌شود.
    """

    def test_the_wide_panel_is_gone(self):
        css = _css()
        self.assertNotIn('has-mega', css)
        self.assertNotIn('grid-template-columns: repeat(var(--cols)', css)

    def test_the_markup_no_longer_marks_them_apart(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('has-mega', html)

    def test_it_is_a_plain_dropdown_again(self):
        """عرضِ معمولی، زیر دکمهٔ خودش — مثل شوراها و درباره موسسه."""
        css = _css()
        self.assertIn('.nav-dd-vices { min-inline-size: 320px; }', css)

    def test_the_panel_starts_short(self):
        """شاخه‌ها بسته باز می‌شوند، پس اسکرولی در کار نیست."""
        rule = self._closed()
        self.assertIn('max-block-size: 0', rule)

    def _closed(self):
        css = _css()
        start = css.index('max-block-size: 0;')
        return css[css.rindex('.vice-sub {', 0, start):
                   css.index('}', start)]

    def test_a_long_faculty_branch_scrolls_inside_itself(self):
        """چهل‌ویک رشته، بلندتر از قدِ صفحه است."""
        css = _css()
        self.assertIn(
            '.nav-dd-faculties .vice-group.has-sub.is-open > .vice-sub', css)
        self.assertIn('overflow-y: auto', css)

    def test_the_ceiling_only_applies_to_an_open_branch(self):
        """بی‌قید که بود، شاخهٔ بستهٔ نامرئی هم پانصد پیکسل جا می‌گرفت
        و منو یک پنلِ بلندِ خالی می‌شد.

        دو کلاسِ \u200E.nav-dd-faculties .vice-sub\u200E بر یک کلاسِ \u200E.vice-sub\u200E
        می‌چربید، پس سقفِ ۵۲۰ پیکسلی جای \u200Emax-block-size: 0\u200E می‌نشست.
        """
        css = _css()
        for line in css.splitlines():
            if 'nav-dd-faculties' in line and 'vice-sub' in line:
                opened = 'is-open' in line or 'focus-within' in line
                self.assertTrue(opened, line.strip())

    def test_one_menu_at_a_time(self):
        from pathlib import Path

        from django.conf import settings

        js = (Path(settings.BASE_DIR) / 'static' / 'js' /
              'main.js').read_text(encoding='utf-8')
        self.assertIn('if (other !== item) { close(other); }', js)

    def test_clicking_a_destination_closes_the_menu(self):
        from pathlib import Path

        from django.conf import settings

        js = (Path(settings.BASE_DIR) / 'static' / 'js' /
              'main.js').read_text(encoding='utf-8')
        self.assertIn("event.target.closest('a[href]')", js)

    def test_closing_goes_through_bootstrap_where_it_drives(self):
        from pathlib import Path

        from django.conf import settings

        js = (Path(settings.BASE_DIR) / 'static' / 'js' /
              'main.js').read_text(encoding='utf-8')
        self.assertIn('window.bootstrap.Dropdown.getInstance(toggle)', js)
