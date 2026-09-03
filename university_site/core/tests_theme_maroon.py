"""تم سایت: زرشکی، نه سرمه‌ای.

پالت متغیرها از اول عنابی بود ولی نوار منو، زیرمنوها، فوتر و کل
حالت تیره سرمه‌ای مانده بودند — یعنی سایت دو هویت رنگی داشت. این
تست‌ها جلوی برگشتِ آبی را می‌گیرند.
"""
from pathlib import Path
import re

from django.conf import settings
from django.test import TestCase

# رنگ نشان شبکه‌های اجتماعی، رنگ خودشان است و آبی می‌ماند.
BRAND = {'#29b6f6', '#0077b5', '#1877f2', '#1da1f2', '#4267b2', '#1a73e8'}


def _css():
    return (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
        encoding='utf-8')


def _blueish(value):
    red, green, blue = (int(value[i:i + 2], 16) for i in (1, 3, 5))
    return blue > red + 20 and blue >= green


class StylesheetIsMaroonTests(TestCase):

    def test_no_navy_hex_is_left(self):
        found = {value.lower() for value in re.findall(r'#[0-9a-fA-F]{6}\b', _css())
                 if _blueish(value.lower())} - BRAND
        self.assertEqual(found, set(), 'رنگ آبی در شیوه‌نامه مانده')

    def test_no_navy_rgba_is_left(self):
        css = _css()
        leftovers = []
        for match in re.finditer(r'rgba\((\d+),\s*(\d+),\s*(\d+)', css):
            red, green, blue = (int(match.group(i)) for i in (1, 2, 3))
            if blue > red + 25 and blue >= green:
                leftovers.append(match.group(0))
        self.assertEqual(leftovers, [])

    def test_the_navbar_is_maroon(self):
        block = _css().split('.main-navbar {')[1].split('}')[0]
        self.assertIn('#2b0a11', block)

    def test_the_dropdown_panel_is_maroon(self):
        block = _css().split('\n.nav-dd {')[1].split('}')[0]
        self.assertIn('#3a0e18', block)

    def test_the_footer_is_maroon(self):
        block = _css().split('.main-footer {')[1].split('}')[0]
        self.assertIn('#1e0a0f', block)

    def test_the_dark_theme_surfaces_are_maroon(self):
        block = _css().split('[data-theme="dark"] {')[1].split('}')[0]
        self.assertIn('--bg-light: #1e0a0f', block)
        self.assertIn('--bg-white: #2a1017', block)

    def test_the_brand_colours_of_the_social_icons_survive(self):
        css = _css()
        self.assertIn('#29b6f6', css)
        self.assertIn('#0077b5', css)


class TemplatesAreMaroonTests(TestCase):
    """رنگ‌های درون‌خطی قالب‌ها هم آبی نمانند — جز پنل ادمین."""

    def test_public_templates_carry_no_navy(self):
        root = Path(settings.BASE_DIR) / 'templates'
        offenders = {}
        for path in root.rglob('*.html'):
            if 'admin' in path.relative_to(root).parts[:1]:
                continue
            text = path.read_text(encoding='utf-8', errors='replace')
            found = {value.lower()
                     for value in re.findall(r'#[0-9a-fA-F]{6}\b', text)
                     if _blueish(value.lower())} - BRAND
            if found:
                offenders[str(path.relative_to(root))] = sorted(found)
        self.assertEqual(offenders, {})
