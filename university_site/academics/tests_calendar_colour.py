"""رنگ دلخواه زمینهٔ باکس‌های تقویم."""
import datetime

from django.test import TestCase

from academics.models import AcademicCalendar


def _step(**extra):
    today = datetime.date.today()
    data = dict(
        title='شروع کلاس‌ها',
        start_date=today,
        end_date=today,
        semester='first',
        academic_year='1404-1405',
    )
    data.update(extra)
    return AcademicCalendar.objects.create(**data)


class CustomCardColourTests(TestCase):
    """هر رنگی که ادمین بخواهد — و متنی که همیشه روی آن خوانده شود."""

    def test_no_colour_means_no_style(self):
        self.assertEqual(_step().card_style, '')

    def test_a_hex_colour_becomes_a_variable(self):
        style = _step(bg_color='#1f6f5c').card_style
        self.assertIn('--acal-bg:#1f6f5c', style)

    def test_dark_background_gets_light_text(self):
        step = _step(bg_color='#0d2137')
        self.assertTrue(step.bg_is_dark)
        self.assertIn('--acal-ink:#ffffff', step.card_style)

    def test_light_background_gets_dark_text(self):
        step = _step(bg_color='#f4e2b8')
        self.assertFalse(step.bg_is_dark)
        self.assertIn('--acal-ink:#0d2137', step.card_style)

    def test_mid_tone_green_counts_as_dark(self):
        """سبز سیر روشناییِ عددی متوسطی دارد ولی متن تیره رویش گم می‌شود."""
        self.assertTrue(_step(bg_color='#1f6f5c').bg_is_dark)

    def test_short_hex_is_accepted(self):
        self.assertEqual(_step(bg_color='#abc').safe_bg_color, '#abc')

    def test_a_bogus_value_is_dropped(self):
        """مقدار داخل صفت style می‌رود؛ هرچه هگز نباشد نباید برسد."""
        step = _step(bg_color='red" onmouseover="alert(1)')
        self.assertEqual(step.safe_bg_color, '')
        self.assertEqual(step.card_style, '')

    def test_named_colours_are_refused(self):
        self.assertEqual(_step(bg_color='rebeccapurple').safe_bg_color, '')


class CustomColourReachesThePageTests(TestCase):
    """رنگ باید از مدل تا صفت style کارت برسد."""

    def _render(self, **extra):
        from django.template.loader import render_to_string
        from core.academic_timeline import build_timeline

        _step(**extra)
        return render_to_string('core/_academic_timeline.html', {
            'timeline': build_timeline(),
            'sections': {},
            'site_settings': None,
        })

    def test_the_colour_is_on_the_card(self):
        html = self._render(bg_color='#1f6f5c')
        self.assertIn('--acal-bg:#1f6f5c', html)

    def test_without_a_colour_no_style_attribute_is_written(self):
        html = self._render()
        self.assertNotIn('--acal-bg', html)

    def test_an_attack_string_never_reaches_the_markup(self):
        attack = 'red" onmouseover="alert(1)'
        html = self._render(bg_color=attack)
        self.assertNotIn('onmouseover', html)
        self.assertNotIn('--acal-bg', html)


class CustomColourStylesheetTests(TestCase):
    """CSS باید رنگ دلخواه را بپذیرد و در نبودش به پیش‌فرض برگردد."""

    def _css(self):
        from pathlib import Path
        from django.conf import settings
        return (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
            encoding='utf-8')

    def test_both_themes_read_the_variable(self):
        css = self._css()
        for selector in ('.acal-card {', '[data-theme="dark"] .acal-card {'):
            start = css.index(chr(10) + selector) + 1
            block = css[start:css.index('}', start)]
            self.assertIn('var(--acal-bg,', block,
                          '%s رنگ دلخواه را نمی‌خواند' % selector)

    def test_the_photo_veil_steps_aside_for_a_chosen_colour(self):
        """پردهٔ روی عکس، رنگ انتخابی را می‌پوشاند اگر برداشته نشود."""
        self.assertIn('.acal-card[style*="--acal-bg"]::after { display: none; }',
                      self._css())
