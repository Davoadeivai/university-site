"""نوار «فوری» زیر بنر: یک خط، روان از چپ به راست."""
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Announcement


def _css():
    return (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
        encoding='utf-8')


def _rule(selector):
    css = _css()
    start = css.index(chr(10) + selector + ' {') + 1
    return css[start:css.index('}', start)]


class TheBarStaysOnOneLineTests(TestCase):
    """با دو اطلاعیه دو خطی می‌شد و روی گوشی کل اسلایدر را می‌پوشاند."""

    def setUp(self):
        cache.clear()
        for index in range(3):
            Announcement.objects.create(
                title='اطلاعیهٔ فوری شمارهٔ %d با عنوانی نسبتاً بلند' % index,
                content='…', is_active=True, is_urgent=True,
                expires_at=timezone.now().date() + timedelta(days=30))

    def _html(self):
        cache.clear()
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_bar_is_height_locked(self):
        rule = _rule('.urgent-bar')
        self.assertIn('overflow: hidden', rule)
        self.assertIn('line-height', rule)

    def test_the_label_never_wraps_below(self):
        self.assertIn('flex-wrap: nowrap', _rule('.urgent-row'))
        self.assertIn('flex: none', _rule('.urgent-label'))

    def test_each_item_stays_on_its_line(self):
        self.assertIn('white-space: nowrap', _rule('.urgent-item'))

    def test_the_ticker_can_actually_shrink(self):
        """بدون min-inline-size صفر، آیتم فلکسی از قاب بیرون می‌زند."""
        rule = _rule('.urgent-ticker')
        self.assertIn('min-inline-size: 0', rule)
        self.assertIn('overflow: hidden', rule)


class ItMovesLeftToRightTests(TestCase):

    def setUp(self):
        cache.clear()
        Announcement.objects.create(
            title='اطلاعیهٔ فوری', content='…', is_active=True,
            is_urgent=True,
            expires_at=timezone.now().date() + timedelta(days=30))

    def _html(self):
        cache.clear()
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_track_is_animated(self):
        self.assertIn('animation: urgentSlide', _rule('.urgent-track'))

    def test_the_direction_is_left_to_right(self):
        css = _css()
        start = css.index('@keyframes urgentSlide')
        block = css[start:css.index('}\n}', start)]
        self.assertIn('from { transform: translateX(-50%)', block)
        self.assertIn('to   { transform: translateX(0)', block)

    def test_the_text_is_written_twice_for_a_seamless_loop(self):
        html = self._html()
        bar = html.split('urgent-bar')[1].split('</div>\n</div>')[0]
        self.assertEqual(bar.count('urgent-run'), 2)

    def test_the_second_copy_is_hidden_from_screen_readers(self):
        """وگرنه هر خبر دو بار خوانده می‌شود."""
        html = self._html()
        second = html.split('urgent-run')[2]
        self.assertIn('aria-hidden="true"', second[:60])

    def test_it_pauses_on_hover(self):
        css = _css()
        self.assertIn('.urgent-bar:hover .urgent-track', css)
        self.assertIn('animation-play-state: paused', css)

    def test_someone_who_dislikes_motion_gets_a_still_bar(self):
        css = _css()
        block = css[css.index('@media (prefers-reduced-motion: reduce)',
                              css.index('.urgent-track')):][:400]
        self.assertIn('animation: none', block)


class TheSpeedFollowsTheContentTests(TestCase):
    """سه خبر با زمانِ یک خبر رد می‌شدند و خوانده نمی‌شدند."""

    def _html(self, count):
        cache.clear()
        Announcement.objects.all().delete()
        for index in range(count):
            Announcement.objects.create(
                title='خبر %d' % index, content='…', is_active=True,
                is_urgent=True,
                expires_at=timezone.now().date() + timedelta(days=30))
        return self.client.get(reverse('core:home')).content.decode()

    def _seconds(self, html):
        chunk = html.split('--urgent-secs: ')[1].split('s')[0]
        return int(chunk)

    def test_one_item_is_quick(self):
        self.assertEqual(self._seconds(self._html(1)), 16)

    def test_three_items_take_longer(self):
        self.assertEqual(self._seconds(self._html(3)), 48)

    def test_the_bar_is_gone_when_nothing_is_urgent(self):
        cache.clear()
        Announcement.objects.all().delete()
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('urgent-bar', html)
