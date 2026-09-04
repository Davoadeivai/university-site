"""اسلایدر باید با هر ابعادی که آپلود می‌شود کنار بیاید.

قاب اسلایدر افقی است. تا امروز هر تصویری با object-fit: cover در آن
بریده می‌شد — که برای عکس افقی درست است و برای پوستر و اینفوگرافیک
و اسکرین‌شات یعنی فقط نوار میانی‌شان دیده می‌شود.
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.admin_search import build_work_queue
from core.models import Slider


def _slide(width, height, **kwargs):
    kwargs.setdefault('title', 'اسلاید')
    kwargs.setdefault('is_active', True)
    row = Slider.objects.create(image='sliders/x.jpg', **kwargs)
    Slider.objects.filter(pk=row.pk).update(
        image_width=width, image_height=height)
    return Slider.objects.get(pk=row.pk)


class AutomaticFitTests(TestCase):
    """مدیر نباید مجبور باشد نسبت تصویر را خودش حساب کند."""

    def test_a_wide_photo_fills_the_frame(self):
        self.assertEqual(_slide(4000, 2250).resolved_fit, 'cover')

    def test_a_portrait_poster_is_shown_whole(self):
        self.assertEqual(_slide(905, 1280).resolved_fit, 'contain')

    def test_a_tall_screenshot_is_shown_whole(self):
        self.assertEqual(_slide(591, 1280).resolved_fit, 'contain')

    def test_a_near_square_photo_is_shown_whole(self):
        self.assertEqual(_slide(1456, 1280).resolved_fit, 'contain')

    def test_a_wide_infographic_still_fills_the_frame(self):
        self.assertEqual(_slide(1080, 608).resolved_fit, 'cover')

    def test_the_admin_choice_beats_the_guess(self):
        self.assertEqual(_slide(4000, 2250, fit='contain').resolved_fit,
                         'contain')
        self.assertEqual(_slide(905, 1280, fit='cover').resolved_fit, 'cover')

    def test_an_unmeasured_image_falls_back_to_filling(self):
        row = Slider.objects.create(title='بی‌ابعاد', image='sliders/x.jpg')
        self.assertEqual(row.resolved_fit, 'cover')

    def test_a_missing_file_does_not_break_saving(self):
        """فایلی که روی دیسک نیست نباید ذخیرهٔ ردیف را بشکند."""
        row = Slider.objects.create(title='بی‌فایل', image='sliders/none.jpg')
        self.assertIsNone(row.image_width)


class SlideRenderingTests(TestCase):

    def setUp(self):
        cache.clear()

    def _html(self):
        cache.clear()
        return self.client.get(reverse('core:home')).content.decode()

    def test_a_whole_shown_slide_gets_a_blurred_backdrop(self):
        _slide(905, 1280)
        html = self._html()
        self.assertIn('uni-hero-slide is-contain', html)
        self.assertIn('<img class="slide-backdrop"', html)

    def test_a_filling_slide_gets_no_backdrop(self):
        _slide(4000, 2250)
        html = self._html()
        self.assertIn('uni-hero-slide is-cover', html)
        self.assertNotIn('<img class="slide-backdrop"', html)

    def test_the_backdrop_is_hidden_from_screen_readers(self):
        _slide(905, 1280)
        backdrop = self._html().split(
            '<img class="slide-backdrop"')[1].split('>')[0]
        self.assertIn('aria-hidden="true"', backdrop)

    def test_the_focus_point_reaches_the_tag(self):
        _slide(4000, 2250, focus='top')
        self.assertIn('object-position: center top', self._html())

    def test_the_stylesheet_shows_a_whole_slide_whole(self):
        from pathlib import Path

        from django.conf import settings

        css = (Path(settings.BASE_DIR) / 'templates' / 'core' /
               'home.html').read_text(encoding='utf-8')
        rule = css.split('.uni-hero-slide.is-contain img.slide-bg {')[1]
        self.assertIn('object-fit: contain', rule.split('}')[0])

    def test_a_whole_slide_does_not_zoom_out_of_its_frame(self):
        from pathlib import Path

        from django.conf import settings

        css = (Path(settings.BASE_DIR) / 'templates' / 'core' /
               'home.html').read_text(encoding='utf-8')
        rule = css.split(
            '.uni-hero-slide.is-contain img.slide-bg {')[1].split('}')[0]
        self.assertIn('transform: none', rule)


class SizeWarningTests(TestCase):
    """پنل باید بگوید کدام فایل برای اسلایدر ساخته نشده."""

    def test_a_good_photo_says_nothing(self):
        self.assertEqual(_slide(4000, 2250).size_warning, '')

    def test_a_portrait_image_is_flagged(self):
        self.assertIn('عمودی', _slide(905, 1280).size_warning)

    def test_a_narrow_image_is_flagged(self):
        self.assertIn('پهنا', _slide(1080, 608).size_warning)

    def test_an_unmeasured_image_is_not_flagged(self):
        row = Slider.objects.create(title='بی‌ابعاد', image='sliders/x.jpg')
        self.assertEqual(row.size_warning, '')


class SliderQueueTests(TestCase):
    """صف کار باید خودش این‌ها را پیدا کند، نه اینکه کسی صفحه را ببیند."""

    def _count(self):
        rows = {item['key']: item for item in build_work_queue()}
        return rows['sliders_wrong_shape']['count']

    def test_a_bad_slide_is_counted(self):
        _slide(591, 1280)
        self.assertEqual(self._count(), 1)

    def test_a_good_slide_is_not(self):
        _slide(4000, 2250)
        self.assertEqual(self._count(), 0)

    def test_an_inactive_slide_is_not_counted(self):
        _slide(591, 1280, is_active=False)
        self.assertEqual(self._count(), 0)

    def test_the_row_links_to_the_sliders(self):
        rows = {item['key']: item for item in build_work_queue()}
        self.assertIn('slider', rows['sliders_wrong_shape']['url'])


class SliderAdminTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'modirslide', 's@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.staff)

    def test_the_list_shows_the_real_dimensions(self):
        _slide(4000, 2250, title='عکس هوایی')
        html = self.client.get('/admin/core/slider/').content.decode()
        self.assertIn('4000×2250', html)

    def test_the_list_shows_the_warning(self):
        _slide(591, 1280, title='اسکرین‌شات')
        html = self.client.get('/admin/core/slider/').content.decode()
        self.assertIn('عمودی', html)

    def test_the_fit_is_editable_from_the_list(self):
        from core.admin import SliderAdmin

        self.assertIn('fit', SliderAdmin.list_editable)
