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


class TheSubmenuDoesNotFlickerTests(TestCase):
    """عبور از روی ردیف‌های میانی، زیرمنو را زیر دست می‌پراند."""

    def test_closing_waits_long_enough_to_cross(self):
        block = _desktop_block()
        self.assertIn('transition-delay: .35s', block)

    def test_opening_ignores_a_passing_pointer(self):
        block = _desktop_block()
        self.assertIn('transition-delay: .12s', block)

    def test_closing_is_slower_than_opening(self):
        """وگرنه همان پرش برمی‌گردد."""
        import re

        block = _desktop_block()
        delays = [float(value) for value in
                  re.findall(r'transition-delay: \.(\d+)s', block)]
        self.assertEqual(len(delays), 2)
        self.assertGreater(max(delays), min(delays))

    def test_a_bridge_covers_the_gap(self):
        block = _desktop_block()
        self.assertIn('.vice-group.has-sub > .vice-sub::before', block)

    def test_a_tall_submenu_can_be_reached(self):
        """زیرمنوی معاونت آخر از پایین صفحه بیرون می‌زد."""
        block = _desktop_block()
        self.assertIn('.nav-dd-vices .vice-sub', block)
        self.assertIn('overflow-y: auto', block)


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
