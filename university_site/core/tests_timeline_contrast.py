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
        `.acal-card {` داخل نسخهٔ `[data-theme="dark"] …` هم پیدا
        می‌شود و چون آن بلوک زودتر در فایل است، تست رنگ حالت تیره را
        روی زمینهٔ روشن می‌سنجد.
        """
        css = _css()
        start = css.index(chr(10) + block_start) + 1
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

    def test_light_theme_card(self):
        self._assert_readable(self._vars('.acal-card {'), self.LIGHT_CARD)

    def test_dark_theme_card(self):
        self._assert_readable(
            self._vars('[data-theme="dark"] .acal-card {'), self.DARK_CARD)


class TimelineCardsLookAlikeTests(TestCase):
    """همهٔ کارت‌ها باید یک شکل باشند، در هر دو تم.

    دو تلاش برای «کم‌جان کردن» مرحلهٔ گذشته هر بار یک گرادیان روشن
    ساخت که در حالت تیره سر جایش می‌ماند و کارت اول و آخر سفید
    درمی‌آمدند. حالا هیچ حالتی زمینهٔ خودش را ندارد، پس چیزی هم برای
    نشت‌کردن نمانده.
    """

    STATES = ('.acal-node.is-past .acal-card',
              '.acal-node.is-now .acal-card')

    def test_no_state_repaints_the_card(self):
        css = _css()
        for state in self.STATES:
            marker = chr(10) + state + ' {'
            if marker not in css:
                continue
            start = css.index(marker) + 1
            block = css[start:css.index('}', start)]
            for line in block.splitlines():
                self.assertFalse(
                    line.strip().startswith('background'),
                    '%s دوباره زمینهٔ خودش را دارد' % state)

    def test_no_state_overrides_the_text_colour(self):
        css = _css()
        for state in self.STATES:
            marker = chr(10) + state + ' {'
            if marker not in css:
                continue
            start = css.index(marker) + 1
            block = css[start:css.index('}', start)]
            self.assertNotIn('--acal-ink', block,
                             '%s رنگ متن جدا دارد' % state)

    def test_done_is_still_marked(self):
        """یکسان‌شدن نباید نشانهٔ «انجام شد» را از بین ببرد."""
        css = _css()
        self.assertIn('.acal-node.is-past .acal-cap i::before', css)
        self.assertIn('\\f00c', css)

    def test_today_is_still_marked(self):
        css = _css()
        start = css.index(chr(10) + '.acal-node.is-now .acal-card {') + 1
        self.assertIn('box-shadow', css[start:css.index('}', start)])


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


class AdminChosenColoursTests(TestCase):
    """رنگ متن تقویم باید از پنل عوض شود، نه از فایل CSS.

    قالب مستقیم رندر می‌شود، نه از راه صفحهٔ اصلی: آنجا بخش تقویم
    فقط وقتی می‌آید که ردیف تقویم ثبت شده باشد، و تست رنگ نباید به
    آن وابسته شود.
    """

    def _render(self, **colours):
        from django.template.loader import render_to_string
        from core.models import SiteSettings

        SiteSettings.objects.all().delete()
        row = SiteSettings.objects.create(**colours)
        html = render_to_string('core/_academic_timeline.html', {
            'site_settings': row,
            'timeline': {'has_data': True, 'nodes': [], 'academic_year': ''},
            'sections': {},
        })
        return row, html

    def test_nothing_is_injected_when_unset(self):
        _row, html = self._render()
        self.assertNotIn('--acal-ink:', html)

    def test_a_chosen_colour_reaches_the_page(self):
        _row, html = self._render(calendar_ink='#7b2d8e')
        self.assertIn('--acal-ink: #7b2d8e', html)

    def test_it_covers_every_state(self):
        """اگر فقط .acal-card نوشته شود، حالت گذشته رنگ را پس می‌زند."""
        _row, html = self._render(calendar_ink='#7b2d8e')
        block = html.split('--acal-ink: #7b2d8e')[0]
        self.assertIn('.acal-node.is-past .acal-card', block)
        self.assertIn('.acal-node.is-now .acal-card', block)

    def test_dark_colours_are_scoped_to_dark(self):
        _row, html = self._render(calendar_ink_dark='#ffd27f')
        block = html.split('--acal-ink: #ffd27f')[0]
        self.assertIn('[data-theme="dark"]', block)

    def test_a_bogus_value_never_reaches_the_style_block(self):
        """مقدار داخل <style> می‌رود؛ هرچه هگز نباشد باید دور ریخته شود."""
        attack = 'red; } body { display:none } .x{color:red'
        row, html = self._render(calendar_ink=attack)
        self.assertEqual(row.calendar_colours, {})
        self.assertNotIn(attack, html)
        self.assertNotIn('--acal-ink:', html)

    def test_named_colours_are_refused_too(self):
        """«red» بی‌خطر است ولی الگو را باز می‌کند؛ فقط هگز می‌پذیریم."""
        row, _html = self._render(calendar_ink='red')
        self.assertEqual(row.calendar_colours, {})

    def test_short_and_long_hex_both_pass(self):
        row, _html = self._render(calendar_ink='#abc',
                                  calendar_ink_soft='#aabbccdd')
        self.assertEqual(len(row.calendar_colours), 2)

    def test_the_admin_exposes_the_fields(self):
        from core.admin import SiteSettingsAdmin
        listed = set()
        for _title, opts in SiteSettingsAdmin.fieldsets:
            listed.update(opts['fields'])
        for field in ('calendar_ink', 'calendar_ink_soft',
                      'calendar_ink_dark', 'calendar_ink_soft_dark'):
            self.assertIn(field, listed)

    def test_the_admin_uses_a_colour_picker(self):
        from django.contrib.admin.sites import AdminSite
        from core.admin import SiteSettingsAdmin
        from core.models import SiteSettings

        admin_obj = SiteSettingsAdmin(SiteSettings, AdminSite())
        field = SiteSettings._meta.get_field('calendar_ink')
        form_field = admin_obj.formfield_for_dbfield(field, None)
        # Input.__init__ کلید type را از attrs برمی‌دارد و در
        # input_type می‌گذارد؛ پس attrs اینجا خالی است، نه ویجت.
        self.assertEqual(form_field.widget.input_type, 'color')

    def test_other_char_fields_keep_their_normal_widget(self):
        from django.contrib.admin.sites import AdminSite
        from core.admin import SiteSettingsAdmin
        from core.models import SiteSettings

        admin_obj = SiteSettingsAdmin(SiteSettings, AdminSite())
        field = SiteSettings._meta.get_field('university_name_fa')
        form_field = admin_obj.formfield_for_dbfield(field, None)
        self.assertNotEqual(form_field.widget.input_type, 'color')
