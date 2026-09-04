"""سربرگ صفحه‌ها — لبهٔ پایینش صاف است، نه مورب."""
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


def _css():
    return (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
        encoding='utf-8')


def _rule(selector):
    css = _css()
    start = css.index(chr(10) + selector + ' {') + 1
    return css[start:css.index('}', start)]


class TheHeaderEdgeIsStraightTests(TestCase):
    """نوارِ کجِ زیر سربرگ در هر صفحه تکرار می‌شد."""

    def test_no_wedge_is_drawn_under_the_header(self):
        self.assertNotIn('.page-header::after', _css())

    def test_nothing_in_the_stylesheet_is_skewed(self):
        """کجی روی نمایشگر پهن چند پیکسل بود و روی باریک ده‌ها."""
        css = _css()
        for skew in ('skewY(', 'skewX(', 'skew('):
            self.assertNotIn(skew, css)

    def test_the_header_still_has_its_gradient(self):
        rule = _rule('.page-header')
        self.assertIn('var(--gradient-primary)', rule)

    def test_it_still_breathes(self):
        """برداشتن نوار نباید یعنی چسبیدن عنوان به لبه."""
        self.assertIn('padding: 60px 0', _rule('.page-header'))


class EveryPageKeepsItsHeaderTests(TestCase):
    """این سربرگ در همهٔ صفحه‌های داخلی هست؛ نباید جایی بشکند."""

    def test_the_inner_pages_still_render(self):
        for name in ('core:about', 'core:councils', 'core:board_founders',
                     'core:board_trustees', 'core:faq'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertIn('page-header',
                              response.content.decode())
