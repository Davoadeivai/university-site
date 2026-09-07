"""نوار «فوری» زیر بنر: یک خط، یک نسخه، آرام از چپ به راست."""
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


def _keyframes():
    css = _css()
    start = css.index('@keyframes urgentSlide')
    return css[start:css.index('}' + chr(10) + '}', start)]


def _announce(count):
    Announcement.objects.all().delete()
    for index in range(count):
        Announcement.objects.create(
            title='اطلاعیهٔ فوری شمارهٔ %d' % index, content='…',
            is_active=True, is_urgent=True,
            expires_at=timezone.now().date() + timedelta(days=30))


class TheBarStaysOnOneLineTests(TestCase):
    """با دو اطلاعیه دو خطی می‌شد و روی گوشی کل اسلایدر را می‌پوشاند."""

    def setUp(self):
        cache.clear()
        _announce(3)

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

    def test_the_ticker_keeps_its_own_height(self):
        """ریل مطلق است؛ بدون قدِ صریح، قاب صفر می‌شود و چیزی دیده نمی‌شود."""
        self.assertIn('block-size: 22px', _rule('.urgent-ticker'))


class OneCopyOnlyTests(TestCase):
    """دو نسخه هم‌زمان دیده می‌شد و نوار دوتایی به‌نظر می‌رسید."""

    def setUp(self):
        cache.clear()
        _announce(2)

    def _html(self):
        cache.clear()
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_old_duplicate_wrapper_is_gone(self):
        self.assertNotIn('urgent-run', self._html())
        self.assertNotIn('.urgent-run', _css())

    def test_each_headline_appears_once(self):
        # فقط داخل خودِ نوار؛ همین عنوان‌ها پایین‌تر در بخش
        # اطلاعیه‌های صفحهٔ اصلی هم می‌آیند.
        ticker = self._html().split('urgent-ticker')[1].split('</div>')[0]
        self.assertEqual(ticker.count('اطلاعیهٔ فوری شمارهٔ 0'), 1)
        self.assertEqual(ticker.count('اطلاعیهٔ فوری شمارهٔ 1'), 1)

    def test_nothing_is_hidden_from_screen_readers_any_more(self):
        """نسخهٔ دوم رفت، پس دیگر چیزی برای پنهان‌کردن نیست."""
        html = self._html()
        ticker = html.split('urgent-ticker')[1].split('</div>')[0]
        self.assertNotIn('aria-hidden', ticker)


class ItMakesOneFullPassLeftToRightTests(TestCase):

    def setUp(self):
        cache.clear()
        _announce(1)

    def test_the_track_is_animated(self):
        self.assertIn('animation: urgentSlide', _rule('.urgent-track'))

    def test_it_starts_at_the_left_corner_already_visible(self):
        """پیش از این از بیرونِ قاب می‌آمد و تا می‌رسید، داشت می‌رفت."""
        block = _keyframes()
        self.assertIn('left: 0;', block)
        self.assertNotIn('translateX(-100%)', block)

    def test_it_holds_still_before_moving(self):
        """موسسه خواست خبر چند ثانیه بایستد تا خوانده شود."""
        import re

        block = _keyframes()
        hold = re.search(r'0%,\s*(\d+)%\s*\{\s*left: 0;', block)
        self.assertIsNotNone(hold, 'مکثی در ابتدای حرکت نیست')
        self.assertGreaterEqual(int(hold.group(1)), 2)

    def test_it_ends_at_the_right_edge(self):
        self.assertIn('left: 100%;', _keyframes())

    def test_the_travel_is_measured_against_the_bar(self):
        """درصدِ ‎left‎ از پهنای قاب می‌آید، پس گذر همیشه کامل است."""
        self.assertIn('left:', _keyframes())

    def test_no_fade_hides_the_edges(self):
        """موسسه خواست متن کامل دیده شود."""
        self.assertNotIn('mask-image', _rule('.urgent-ticker'))

    def test_it_pauses_on_hover(self):
        css = _css()
        self.assertIn('.urgent-bar:hover .urgent-track', css)
        self.assertIn('animation-play-state: paused', css)

    def test_someone_who_dislikes_motion_gets_a_still_bar(self):
        css = _css()
        block = css[css.index('@media (prefers-reduced-motion: reduce)',
                              css.index('.urgent-track')):][:400]
        self.assertIn('animation: none', block)
        self.assertIn('position: static', block)


class TheSpeedIsUnhurriedTests(TestCase):
    """سه خبر با زمانِ یک خبر رد می‌شدند و خوانده نمی‌شدند."""

    def _seconds(self, count):
        cache.clear()
        _announce(count)
        html = self.client.get(reverse('core:home')).content.decode()
        return int(html.split('--urgent-secs: ')[1].split('s')[0])

    def test_one_item_is_slow_enough_to_read(self):
        self.assertGreaterEqual(self._seconds(1), 55)

    def test_it_got_slower_twice(self):
        """اول ۱۶ ثانیه بود، بعد ۳۴، و باز هم تند بود."""
        self.assertGreater(self._seconds(1), 34)

    def test_more_items_take_proportionally_longer(self):
        self.assertEqual(self._seconds(3), 3 * self._seconds(1))

    def test_the_bar_is_gone_when_nothing_is_urgent(self):
        cache.clear()
        Announcement.objects.all().delete()
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('urgent-bar', html)
