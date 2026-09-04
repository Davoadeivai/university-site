"""چند اسلاید روی صفحهٔ اصلی بیاید — تصمیم مدیر، نه عددی در کد."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import SiteSettings, Slider


class HomeSliderCountTests(TestCase):
    """مدیر هفت اسلاید ساخته بود و فقط پنج‌تا دیده می‌شد."""

    def setUp(self):
        cache.clear()
        for index in range(7):
            Slider.objects.create(
                title='اسلاید %d' % index, order=index, is_active=True,
                image='sliders/s%d.jpg' % index)

    def _shown(self):
        html = self.client.get(reverse('core:home')).content.decode()
        hero = html.split('id="heroTrack"')[1].split('/track')[0]
        return hero.count('uni-hero-slide')

    def test_seven_slides_are_all_shown_by_default(self):
        self.assertEqual(self._shown(), 7)

    def test_the_panel_decides_how_many(self):
        SiteSettings.objects.create(home_slider_count=3)
        cache.clear()
        self.assertEqual(self._shown(), 3)

    def test_a_bigger_number_than_there_are_slides_is_harmless(self):
        SiteSettings.objects.create(home_slider_count=40)
        cache.clear()
        self.assertEqual(self._shown(), 7)

    def test_there_is_no_ceiling_any_more(self):
        """موسسه خواست محدودیت برداشته شود.

        وزن صفحه با سقف حل نمی‌شد: جز اسلاید اول، بقیه تنبل بار
        می‌شوند و تا دیده‌نشدن دانلود نمی‌شوند.
        """
        for index in range(7, 25):
            Slider.objects.create(
                title='اسلاید %d' % index, order=index, is_active=True,
                image='sliders/s%d.jpg' % index)
        SiteSettings.objects.create(home_slider_count=0)
        cache.clear()
        self.assertEqual(self._shown(), 25)

    def test_zero_means_every_slide(self):
        SiteSettings.objects.create(home_slider_count=0)
        cache.clear()
        self.assertEqual(self._shown(), 7)

    def test_a_number_still_limits_when_the_panel_asks(self):
        """برداشتن سقف یعنی اختیار، نه اجبار به نمایش همه."""
        SiteSettings.objects.create(home_slider_count=4)
        cache.clear()
        self.assertEqual(self._shown(), 4)

    def test_only_the_first_slide_loads_eagerly(self):
        """همین است که برداشتن سقف را بی‌خطر می‌کند."""
        html = self.client.get(reverse('core:home')).content.decode()
        hero = html.split('id="heroTrack"')[1].split('/track')[0]
        self.assertEqual(hero.count('loading="eager"'), 1)
        self.assertEqual(hero.count('loading="lazy"'), 6)

    def test_no_settings_row_still_renders(self):
        """دیتابیس تازه هنوز ردیف تنظیمات ندارد."""
        self.assertFalse(SiteSettings.objects.exists())
        self.assertEqual(
            self.client.get(reverse('core:home')).status_code, 200)

    def test_an_inactive_slide_is_left_out(self):
        Slider.objects.filter(order=0).update(is_active=False)
        cache.clear()
        self.assertEqual(self._shown(), 6)

    def test_the_order_is_honoured(self):
        SiteSettings.objects.create(home_slider_count=2)
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('اسلاید 0', html)
        self.assertNotIn('اسلاید 6', html)

    def test_the_panel_offers_the_field(self):
        from core.admin import SiteSettingsAdmin

        self.assertIn('home_slider_count', str(SiteSettingsAdmin.fieldsets))

    def test_the_field_accepts_any_number(self):
        SiteSettings(home_slider_count=99).full_clean()

    def test_zero_is_a_valid_choice(self):
        SiteSettings(home_slider_count=0).full_clean()


class HeroHeightTests(TestCase):
    """اسلاید تمام‌ارتفاع بود و معلوم نبود صفحه ادامه دارد."""

    def _css(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('.uni-hero-wrap {')[1].split('}')[0]

    def setUp(self):
        cache.clear()

    def test_the_hero_no_longer_fills_the_whole_screen(self):
        css = self._css()
        self.assertNotIn('height: 100vh', css)
        self.assertNotIn('height: 100svh', css)

    def test_it_uses_small_viewport_units(self):
        """نوار نشانی موبایل داخل vh حساب می‌شود و اسلاید می‌پرد."""
        self.assertIn('svh', self._css())

    def test_an_old_browser_still_gets_a_height(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('@supports not (height: 1svh)', html)

    def test_it_never_grows_past_a_sensible_ceiling(self):
        """روی نمایشگر بلند، اسلاید نباید یک دیوار عکس شود."""
        self.assertIn('max-height', self._css())
