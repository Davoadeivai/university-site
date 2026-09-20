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

    def test_no_script_moves_the_bar_behind_the_stylesheet(self):
        """ریشهٔ واقعیِ «از چپ وارد نمی‌شود».

        در \u200Emain.js\u200E یک تایمر بیست‌میلی‌ثانیه‌ای بود که خودِ قاب را با
        \u200Estyle.transform\u200E به راست می‌برد و متن را هم دو بار می‌نوشت.
        استایل درون‌خطی بر هر قاعده‌ای می‌چربد، پس هر چه در CSS
        اصلاح می‌شد بی‌اثر می‌ماند.
        """
        from pathlib import Path

        from django.conf import settings

        script = (Path(settings.BASE_DIR) / 'static' / 'js' /
                  'main.js').read_text(encoding='utf-8')
        self.assertNotIn("querySelectorAll('.urgent-ticker')", script)
        self.assertNotIn('.urgent-ticker"', script)
        for hint in ('ticker.style.transform', 'ticker.innerHTML'):
            self.assertNotIn(hint, script)

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
        """یک ریل، یک حرکت — خبرها زنجیروار داخلش می‌آیند."""
        self.assertIn('animation: urgentSlide', _rule('.urgent-track'))

    def test_it_enters_from_outside_the_left_edge(self):
        """موسسه خواست خبر کامل از سمت چپ وارد شود.

        پیش از این لحظهٔ صفر همان‌جا کنار لبهٔ چپ ظاهر می‌شد؛ حالا از
        بیرونِ قاب می‌آید تو.
        """
        block = _keyframes()
        self.assertIn('translateX(-100%)', block)
        self.assertIn('left: 0;', block)

    def test_the_pause_happens_before_the_entry_not_in_the_middle_of_it(self):
        """مکث باید بیرونِ قاب باشد، نه وسطِ راه.

        نسخهٔ پیشین در آن درصد به \u200EtranslateX(0)\u200E می‌رسید، یعنی خبر
        باید کل پهنای خودش را در همان چند درصدِ کوتاه می‌دوید و
        یک‌باره نزدیک میانهٔ نوار ظاهر می‌شد. حالا تا لحظهٔ راه‌افتادن
        همان بیرون می‌ماند و بعد یک‌نواخت می‌آید.
        """
        import re

        block = _keyframes()
        pause = re.search(
            r'(\d+)%\s*\{\s*left: 0;\s*transform: translateX\(-100%\)',
            block[block.index('0%') + 2:])
        self.assertIsNotNone(pause, 'مرحلهٔ مکث در انیمیشن نیست')
        self.assertNotIn('transform: translateX(0); }\n    100%',
                         block.replace('\r', ''))

    def test_the_speed_never_changes_mid_run(self):
        """تنها جایی که \u200EtranslateX(0)\u200E می‌آید، پایانِ حرکت است."""
        self.assertEqual(_keyframes().count('translateX(0)'), 1)

    def test_the_rail_is_as_wide_as_its_text(self):
        """ریشهٔ «خبر از وسط شروع می‌شود».

        ریل مطلق است و فقط left دارد، پس پهنای جعبه‌اش حداکثر
        اندازهٔ قاب می‌شد — نه اندازهٔ متن. عنوانِ بلندتر از قاب یعنی
        عقب‌بردن صد درصدی فقط یک قاب عقب می‌برد و دنبالهٔ متن از همان
        لحظهٔ صفر دیده می‌شد. سه بار کی‌فریم عوض شد و مشکل سر جایش
        ماند، چون جای اشکال اینجا بود.
        """
        self.assertIn('inline-size: max-content', _rule('.urgent-track'))

    def test_the_bar_reaches_the_edges_of_the_screen(self):
        """«از لبهٔ چپ» یعنی لبهٔ صفحه، نه لبهٔ ستون میانی.

        \u200E.container\u200E روی نمایشگر بزرگ حدود ۳۰۰ پیکسل از هر سو تو
        می‌آمد و خبر از همان‌جا وارد می‌شد.
        """
        self.assertIn('max-inline-size: 100%', _rule('.urgent-bar > .container'))

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

    def test_the_headlines_run_as_one_chain(self):
        """موسسه زنجیر خواست، نه تکی‌تکی.

        یک بار هر خبر انیمیشن و تأخیر خودش را گرفت و نوار میان دو
        خبر خالی می‌ماند. حالا همه در یک ریل‌اند و یک‌جا می‌آیند.
        """
        cache.clear()
        _announce(3)
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('.urgent-item:nth-child', html)
        self.assertNotIn('animation-delay', html)
        ticker = html.split('urgent-ticker')[1].split('</div>')[0]
        for index in range(3):
            self.assertIn('اطلاعیهٔ فوری شمارهٔ %d' % index, ticker)

    def test_a_line_marks_where_one_headline_ends(self):
        """زنجیر یعنی بی‌فاصله، پس مرزشان باید دیده شود."""
        self.assertIn('.urgent-item + .urgent-item::before', _css())

    def test_a_headline_has_no_movement_of_its_own(self):
        """حرکت مالِ ریل است؛ خبرها فقط سوارش‌اند.\u200Ebackwards\u200E"""
        self.assertNotIn('animation', _rule('.urgent-item'))

    def test_the_chain_leaves_at_the_right_edge(self):
        """آخرین خبر هم باید کامل بیرون برود، نه اینکه وسط قطع شود."""
        cache.clear()
        _announce(1)
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('100% { left: 100%; transform: translateX(0); }', html)

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


class TheTickerStartsAtTheFarLeftTests(TestCase):
    """خبر باید از گوشهٔ چپ آغاز شود، نه از میانهٔ صفحه.

    صفحه راست‌به‌چپ است، پس خبرهای داخل ریل از لبهٔ راستِ آن شروع
    می‌شدند — درست کنار برچسب «فوری» و در میانهٔ صفحه. حرکت از همان
    نقطه به راست می‌رفت و نیمهٔ چپِ نوار همیشه خالی بود.
    """

    def _css(self):
        from pathlib import Path

        from django.conf import settings

        return (Path(settings.BASE_DIR) / 'static' / 'css' /
                'main.css').read_text(encoding='utf-8')

    def _rule(self, selector):
        css = self._css()
        start = css.index('\n' + selector + ' {')
        return css[start:css.index('}', start)]

    def test_the_rail_is_laid_out_left_to_right(self):
        self.assertIn('direction: ltr', self._rule('.urgent-track'))

    def test_each_headline_stays_right_to_left(self):
        rule = self._rule('.urgent-item')
        self.assertIn('direction: rtl', rule)
        self.assertIn('unicode-bidi: isolate', rule)

    def test_it_still_begins_flush_with_the_left_edge(self):
        self.assertIn('left: 0;', self._rule('.urgent-track'))
