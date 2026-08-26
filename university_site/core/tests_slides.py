"""موسسه خواست هیچ نوشته‌ای روی اسلایدهای صفحهٔ اصلی نباشد."""
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import Slider


class SlideTextRemovedTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        Slider.objects.create(
            title='عنوان روی اسلاید', subtitle='زیرعنوان روی اسلاید',
            badge_text='خبر فوری', link_text='بیشتر بخوانید',
            link='/news/', order=1, is_active=True)

    def setUp(self):
        cache.clear()

    def _hero(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="heroTrack"')[1].split('/track')[0]

    def test_the_home_page_still_opens(self):
        self.assertEqual(
            self.client.get(reverse('core:home')).status_code, 200)

    def _visible(self):
        """اسلایدها بدون متن جایگزین تصویر.

        alt روی صفحه دیده نمی‌شود و برای صفحه‌خوان لازم است، پس
        نباید با نوشتهٔ روی اسلاید اشتباه گرفته شود.
        """
        import re
        return re.sub(r'alt="[^"]*"', '', self._hero())

    def test_no_title_is_painted_on_the_slide(self):
        hero = self._visible()
        self.assertNotIn('عنوان روی اسلاید', hero)
        self.assertNotIn('زیرعنوان روی اسلاید', hero)

    def test_no_badge_or_button_either(self):
        hero = self._visible()
        self.assertNotIn('خبر فوری', hero)
        self.assertNotIn('بیشتر بخوانید', hero)

    def test_the_text_block_itself_is_gone(self):
        self.assertNotIn('uni-slide-body', self._hero())

    def test_the_image_survives(self):
        """برداشتن نوشته نباید خودِ اسلاید را بردارد."""
        hero = self._hero()
        self.assertIn('uni-hero-slide', hero)
        self.assertIn('slide-bg', hero)

    def test_the_title_is_still_the_alt_text(self):
        """متن جایگزین تصویر برای صفحه‌خوان لازم است، روی صفحه دیده نمی‌شود."""
        self.assertIn('alt="عنوان روی اسلاید"', self._hero())

    def test_the_demo_slides_carry_no_text_either(self):
        Slider.objects.all().delete()
        cache.clear()
        hero = self._hero()
        self.assertIn('slide-bg', hero)
        self.assertNotIn('uni-slide-body', hero)

    def test_the_scrim_was_lightened(self):
        """پرده تیره فقط برای خوانا شدن آن نوشته‌ها بود."""
        css = (Path(settings.BASE_DIR) / 'templates' / 'core' / 'home.html'
               ).read_text(encoding='utf-8')
        block = css.split('.uni-hero-slide::after')[1].split('}')[0]
        self.assertNotIn('rgba(0,0,0,.72)', block)
