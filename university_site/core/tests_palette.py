"""پالت عنابی و طلا — رنگی که خوانده نشود، رنگ خوبی نیست."""
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


def _css():
    return (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
        encoding='utf-8')


def _tokens():
    """متغیرهای پالت از بلوک :root."""
    css = _css()
    start = css.index(':root {')
    block = css[start:css.index('}', start)]
    found = {}
    for line in block.splitlines():
        line = line.strip()
        if line.startswith('--') and '#' in line:
            name, _, value = line.partition(':')
            colour = value.strip().split(';')[0].strip()
            if colour.startswith('#') and len(colour) in (4, 7):
                found[name.strip()] = colour
    return found


def _luminance(colour):
    value = colour.lstrip('#')
    if len(value) == 3:
        value = ''.join(ch * 2 for ch in value)
    channels = []
    for i in (0, 2, 4):
        c = int(value[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928
                        else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(front, back):
    a, b = _luminance(front), _luminance(back)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


class PaletteContrastTests(TestCase):
    """هر رنگ متنی باید روی زمینه‌اش خوانا باشد."""

    def test_body_text_on_paper(self):
        tokens = _tokens()
        ratio = contrast(tokens['--text-dark'], tokens['--bg-light'])
        self.assertGreaterEqual(ratio, 7, 'متن اصلی %.1f:۱' % ratio)

    def test_muted_text_on_paper(self):
        tokens = _tokens()
        ratio = contrast(tokens['--text-muted'], tokens['--bg-light'])
        self.assertGreaterEqual(ratio, 4.5, 'متن کم‌رنگ %.1f:۱' % ratio)

    def test_primary_on_paper(self):
        """عنابی روی کاغذ برای تیتر و لینک استفاده می‌شود."""
        tokens = _tokens()
        ratio = contrast(tokens['--primary'], tokens['--bg-light'])
        self.assertGreaterEqual(ratio, 4.5, 'عنابی %.1f:۱' % ratio)

    def test_white_on_primary(self):
        """دکمه‌های اصلی متن سفید روی عنابی دارند."""
        ratio = contrast('#ffffff', _tokens()['--primary'])
        self.assertGreaterEqual(ratio, 4.5, 'سفید روی عنابی %.1f:۱' % ratio)

    def test_gold_is_readable_as_text(self):
        """طلا فقط تزئین نیست؛ شعار صفحهٔ ریاست با آن نوشته می‌شود."""
        tokens = _tokens()
        ratio = contrast(tokens['--gold-ink'], tokens['--bg-light'])
        self.assertGreaterEqual(ratio, 4.5, 'طلای متنی %.1f:۱' % ratio)

    def test_decorative_gold_is_kept_separate(self):
        """--secondary برای حاشیه است و لازم نیست به ۴٫۵ برسد؛
        اما نباید جای طلای متنی را بگیرد."""
        tokens = _tokens()
        self.assertNotEqual(tokens['--secondary'], tokens['--gold-ink'])

    def test_success_and_danger_stay_readable(self):
        tokens = _tokens()
        for name in ('--accent', '--danger'):
            ratio = contrast(tokens[name], tokens['--bg-light'])
            self.assertGreaterEqual(ratio, 4.5,
                                    '%s = %.1f:۱' % (name, ratio))


class PaletteCoherenceTests(TestCase):
    """پالت باید یک خانواده باشد، نه چند رنگ بی‌ربط."""

    def test_no_leftover_blue_primary(self):
        """پیش از این --primary خاکستری بود و --primary-light سبز."""
        tokens = _tokens()
        self.assertNotEqual(tokens['--primary'], '#8d9393')
        self.assertNotEqual(tokens.get('--primary-light'), '#6d824a')

    def test_primary_light_is_the_same_hue(self):
        """روشن‌تر باید همان رنگ باشد، نه رنگی دیگر."""
        import colorsys
        tokens = _tokens()

        def hue(colour):
            value = colour.lstrip('#')
            rgb = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            return colorsys.rgb_to_hsv(*rgb)[0] * 360

        gap = abs(hue(tokens['--primary']) - hue(tokens['--primary-light']))
        self.assertLess(min(gap, 360 - gap), 20,
                        'عنابی و روشن‌ترش هم‌خانواده نیستند')

    def test_the_gradients_use_the_palette(self):
        css = _css()
        start = css.index('--gradient-brand:')
        line = css[start:css.index(';', start)]
        self.assertIn('4e1220', line)
        self.assertIn('c9a34e', line)


class WcuPlaqueStyleTests(TestCase):
    """قاب برداشته شد؛ ترتیب و خوانایی باید بماند."""

    def _rule(self, selector):
        css = _css()
        start = css.index(chr(10) + selector + ' {') + 1
        return css[start:css.index('}', start)]

    def test_the_frame_is_gone(self):
        rule = self._rule('.wcu-plaque')
        for gone in ('border:', 'background:', 'box-shadow:'):
            self.assertNotIn(gone, rule, 'قاب هنوز %s دارد' % gone)

    def test_the_gold_rules_left_with_the_frame(self):
        self.assertNotIn('.wcu-plaque::before', _css())

    def test_the_motto_stands_out(self):
        rule = self._rule('.wcu-motto')
        self.assertIn('font-style: italic', rule)
        self.assertIn('var(--gold-ink', rule)

    def test_the_address_looks_like_a_link(self):
        """بدون نشانهٔ دیداری، کاربر نمی‌داند قابل کلیک است."""
        rule = self._rule('.wcu-link-text')
        self.assertIn('border-block-end', rule)

    def test_the_address_is_a_real_link(self):
        from core.models import PresidencyOffice
        PresidencyOffice.objects.all().delete()
        PresidencyOffice.objects.create(
            president_name='رئیس', president_website='https://WCM-Society.Com')
        html = self.client.get(reverse('core:presidency')).content.decode()
        block = html.split('wcu-link')[0][-260:]
        self.assertIn('href="https://WCM-Society.Com"', html)
        self.assertIn('target="_blank"', html.split('wcu-link')[1][:200])


class PresidencyMenuTests(TestCase):
    """برچسب تکراری «ریاست» بالای لینک هم‌نامش برداشته شد."""

    def test_the_word_appears_once_in_the_menu(self):
        """«حوزه ریاست» هم در کامنت است و هم روی دکمه، پس لنگر باید
        خودِ لینک باشد نه عنوان منو."""
        html = self.client.get(reverse('core:home')).content.decode()
        anchor = 'fa-user-tie'
        menu = html.split(anchor)[1].split('</ul>')[0]
        self.assertEqual(menu.count('>ریاست<'), 1,
                         'کلمهٔ ریاست %d بار در منوست' % menu.count('>ریاست<'))

    def test_the_link_survived(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn(reverse('core:presidency'), html)
