"""تقویم آموزشی — خوانایی متن روی کارت‌ها.

چرا این فایل هست
────────────────
رنگ کم‌کنتراست هیچ خطایی نمی‌دهد و هیچ تستی را نمی‌شکند؛ فقط
بازدیدکننده متن را نمی‌خواند. یک بار همین اتفاق افتاد: برای حالت
تیره فقط دو رنگ از پنج رنگ متن بازنویسی شده بود و بقیه رنگ حالت
روشن را نگه داشتند.
"""
from pathlib import Path

from django.conf import settings
from django.test import TestCase


def _css():
    return (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
        encoding='utf-8')


def _luminance(hex_colour):
    """روشناییِ نسبی طبق WCAG."""
    value = hex_colour.lstrip('#')
    if len(value) == 3:
        value = ''.join(ch * 2 for ch in value)
    channels = []
    for i in (0, 2, 4):
        c = int(value[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928
                        else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fore, back):
    a, b = _luminance(fore), _luminance(back)
    light, dark = max(a, b), min(a, b)
    return (light + 0.05) / (dark + 0.05)


class TimelineContrastTests(TestCase):
    """هر رنگ متنی که در CSS نوشته شده باید روی زمینه‌اش خوانا باشد."""

    # زمینهٔ واقعی کارت پس از پردهٔ روی تصویر
    LIGHT_CARD = '#f4f7fa'
    DARK_CARD = '#111f2f'

    def _vars(self, block_start):
        """متغیرهای --acal-* داخل یک بلوک CSS.

        لنگر سطر ابتدای انتخابگر لازم است: بدون آن،
        `.acal-node.is-past .acal-card {` داخل نسخهٔ
        `[data-theme="dark"] …` هم پیدا می‌شود و چون آن بلوک زودتر
        در فایل است، تست رنگ حالت تیره را روی زمینهٔ روشن می‌سنجد.
        """
        css = _css()
        start = css.index('\n' + block_start) + 1
        block = css[start:css.index('}', start)]
        found = {}
        for line in block.splitlines():
            line = line.strip()
            if line.startswith('--acal-') and '#' in line:
                name, _, value = line.partition(':')
                colour = value.strip().rstrip(';').strip()
                if colour.startswith('#'):
                    found[name.strip()] = colour
        return found

    def _assert_readable(self, colours, background, floor=4.5):
        self.assertTrue(colours, 'هیچ رنگی در این بلوک پیدا نشد')
        for name, colour in colours.items():
            ratio = contrast(colour, background)
            self.assertGreaterEqual(
                ratio, floor,
                '%s = %s روی %s فقط %.1f:۱ کنتراست دارد'
                % (name, colour, background, ratio))

    def test_light_theme_default_card(self):
        self._assert_readable(self._vars('.acal-card {'), self.LIGHT_CARD)

    def test_light_theme_past_card(self):
        self._assert_readable(
            self._vars('.acal-node.is-past .acal-card {'), self.LIGHT_CARD)

    def test_light_theme_current_card(self):
        self._assert_readable(
            self._vars('.acal-node.is-now .acal-card {'), self.LIGHT_CARD)

    def test_dark_theme_default_card(self):
        self._assert_readable(
            self._vars('[data-theme="dark"] .acal-card {'), self.DARK_CARD)

    def test_dark_theme_past_card(self):
        self._assert_readable(
            self._vars('[data-theme="dark"] .acal-node.is-past .acal-card {'),
            self.DARK_CARD)

    def test_dark_theme_current_card(self):
        self._assert_readable(
            self._vars('[data-theme="dark"] .acal-node.is-now .acal-card {'),
            self.DARK_CARD)


class TimelineTextPlumbingTests(TestCase):
    """همهٔ متن‌ها باید از همان دو متغیر بخوانند، نه رنگ خودشان."""

    def test_every_text_rule_uses_the_variables(self):
        css = _css()
        for selector in ('.acal-day {', '.acal-month {',
                         '.acal-label {', '.acal-desc {', '.acal-go {'):
            start = css.index('\n' + selector) + 1
            block = css[start:css.index('}', start)]
            self.assertIn('var(--acal-', block,
                          '%s رنگ ثابت خودش را دارد' % selector)

    def test_the_photo_never_touches_the_text(self):
        """پرده روی تصویر لازم است؛ بدون آن خوانایی به عکس وابسته است."""
        css = _css()
        self.assertIn('.acal-card.has-img::after', css)
        for theme_rule in ('.acal-card.has-img::after',
                           '[data-theme="dark"] .acal-card.has-img::after'):
            start = css.index(theme_rule)
            self.assertIn('linear-gradient', css[start:css.index('}', start)])

    def test_no_text_is_below_eleven_pixels(self):
        """rem زیر ۰٫۶۹ یعنی کمتر از ۱۱ پیکسل — روی موبایل ناخوانا."""
        import re
        css = _css()
        for selector in ('.acal-desc {', '.acal-go {'):
            start = css.index('\n' + selector) + 1
            block = css[start:css.index('}', start)]
            for size in re.findall(r'font-size:\s*([\d.]+)rem', block):
                self.assertGreaterEqual(
                    float(size) * 16, 11,
                    '%s فونت %srem دارد' % (selector, size))


class TimelineCardsLookAlikeTests(TestCase):
    """هر حالتی که کارت را در تم روشن رنگ می‌کند، باید نسخهٔ تیره هم داشته باشد.

    قاعدهٔ «مرحلهٔ گذشته» یک گرادیان سفید می‌گذاشت و نسخهٔ تیره‌اش
    فقط رنگ متن را بازنویسی می‌کرد، نه پس‌زمینه را. نتیجه در حالت
    تیره: کارت اول و آخر تقویم سفید و بقیه تیره — بدون هیچ خطایی،
    فقط یک صفحهٔ ناهماهنگ.
    """

    STATES = ('.acal-node.is-past .acal-card',
              '.acal-node.is-now .acal-card')

    def _block(self, selector, css=None):
        css = css or _css()
        start = css.index(chr(10) + selector + ' {') + 1
        return css[start:css.index('}', start)]

    def test_each_state_has_a_dark_counterpart(self):
        css = _css()
        for state in self.STATES:
            light = self._block(state, css)
            if 'background' not in light:
                continue
            dark_selector = '[data-theme="dark"] ' + state
            self.assertIn(dark_selector + ' {', css,
                          '%s در حالت تیره بازنویسی نشده' % state)
            dark = self._block(dark_selector, css)
            self.assertIn('background', dark,
                          '%s فقط رنگ متن را عوض می‌کند، نه پس‌زمینه'
                          % dark_selector)

    def test_dark_states_are_not_painted_white(self):
        """هیچ کارتی در حالت تیره نباید زمینهٔ روشن بگیرد.

        فقط اعلان background بررسی می‌شود، نه کل بلوک: رنگ متن در
        حالت تیره عمداً سفید است و بلوک را کاملاً رد می‌کرد.
        """
        css = _css()
        for state in self.STATES:
            dark = self._block('[data-theme="dark"] ' + state, css)
            painted = [ln for ln in dark.splitlines()
                       if ln.strip().startswith('background')]
            for line in painted:
                for bad in ('#ffffff', '#fff;', '#f7f9fc', '#fdf8ec'):
                    self.assertNotIn(bad, line,
                                     '%s زمینهٔ روشن %s دارد' % (state, bad))

    def test_the_no_color_mix_fallback_covers_dark_too(self):
        """مرورگر بدون color-mix هم نباید کارت سفید بسازد."""
        css = _css()
        start = css.index('@supports not (color: color-mix')
        block = css[start:css.index(chr(10) + '}', start)]
        self.assertIn('[data-theme="dark"] .acal-node.is-past .acal-card',
                      block)
