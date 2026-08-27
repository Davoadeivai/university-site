"""اسلایدر صفحهٔ اصلی — نوارها، پیش‌نمایش، کشیدن، و توقف."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import Slider


class HeroControlsTests(TestCase):
    """با هفت اسلاید، کاربر باید بداند چندتاست و چقدر مانده."""

    def setUp(self):
        cache.clear()
        for index in range(7):
            Slider.objects.create(
                title='اسلاید %d' % index, order=index, is_active=True,
                image='sliders/s%d.jpg' % index)

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_dots_are_gone(self):
        html = self._html()
        self.assertNotIn('uni-hero-dots', html)
        self.assertNotIn('heroDots', html)

    def test_the_bars_container_is_there(self):
        self.assertIn('id="heroBars"', self._html())

    def test_the_bars_are_a_tablist(self):
        """صفحه‌خوان باید بفهمد این‌ها انتخاب‌گر اسلایدند، نه تزئین."""
        # لنگر روی id، نه نام کلاس: نام کلاس اول در CSS ظاهر می‌شود
        bars = self._html().split('id="heroBars"')[1].split('>')[0]
        self.assertIn('role="tablist"', bars)
        self.assertIn('aria-label', bars)

    def test_the_script_builds_one_bar_per_slide(self):
        html = self._html()
        self.assertIn("for (var i = 0; i < total; i++)", html)
        self.assertIn("uni-hero-bar", html)
        self.assertIn("aria-selected", html)


class HeroDirectionTests(TestCase):
    """دکمهٔ راست «بعدی» بود ولی یک اسلاید عقب می‌رفت."""

    def setUp(self):
        cache.clear()
        for index in range(3):
            Slider.objects.create(
                title='اسلاید %d' % index, order=index, is_active=True,
                image='sliders/s%d.jpg' % index)

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_next_button_says_next(self):
        button = self._html().split('id="heroNext"')[0].split('<button')[-1]
        self.assertIn('aria-label="اسلاید بعدی"', self._html())
        self.assertIn('next', button)

    def test_the_next_button_moves_forward(self):
        html = self._html()
        block = html.split("nextBtn.addEventListener")[1].split('}')[0]
        self.assertIn('jump(1)', block)

    def test_the_previous_button_moves_back(self):
        html = self._html()
        block = html.split("prevBtn.addEventListener")[1].split('}')[0]
        self.assertIn('jump(-1)', block)

    def test_in_a_right_to_left_page_next_sits_on_the_right(self):
        html = self._html()
        self.assertIn('.uni-hero-arrow.next { right: 20px; }', html)
        self.assertIn('.uni-hero-arrow.prev { left:  20px; }', html)

    def test_the_arrow_keys_work(self):
        html = self._html()
        self.assertIn("'ArrowRight'", html)
        self.assertIn("'ArrowLeft'", html)


class HeroSwipeTests(TestCase):
    """کشیدن با انگشت نباید اسکرول عمودی را بدزدد."""

    def setUp(self):
        cache.clear()
        Slider.objects.create(title='یک', order=0, is_active=True,
                              image='sliders/a.jpg')
        Slider.objects.create(title='دو', order=1, is_active=True,
                              image='sliders/b.jpg')

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_a_mostly_vertical_swipe_is_ignored(self):
        """کاربر دارد صفحه را پایین می‌برد، نه اسلاید را عوض می‌کند."""
        html = self._html()
        self.assertIn('Math.abs(dx) > Math.abs(dy)', html)

    def test_the_gesture_does_not_block_scrolling(self):
        """passive یعنی مرورگر برای اسکرول منتظر اسکریپت نمی‌ماند."""
        html = self._html()
        block = html.split("touchstart")[1][:200]
        self.assertIn('passive: true', block)


class HeroPeekTests(TestCase):
    """«بعدی چیست؟» همان چیزی است که کاربر را نگه می‌دارد."""

    def setUp(self):
        cache.clear()
        for index in range(4):
            Slider.objects.create(
                title='اسلاید %d' % index, order=index, is_active=True,
                image='sliders/s%d.jpg' % index)

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_preview_is_in_the_markup(self):
        self.assertIn('id="heroPeek"', self._html())

    def test_it_stays_hidden_until_the_script_fills_it(self):
        """قاب خالی بدتر از نبودن است."""
        peek = self._html().split('id="heroPeek"')[1].split('>')[0]
        self.assertIn('hidden', peek)

    def test_it_is_a_button_not_a_decoration(self):
        html = self._html()
        self.assertIn('<button class="uni-hero-next"', html)
        self.assertIn("peek.addEventListener('click'", html)

    def test_its_thumbnail_is_hidden_from_screen_readers(self):
        """تصویر تکراری اسلاید بعدی چیزی به صفحه‌خوان اضافه نمی‌کند."""
        peek = self._html().split('id="heroPeek"')[1].split('</button>')[0]
        self.assertIn('aria-hidden="true"', peek)

    def test_it_is_not_shown_on_a_phone(self):
        self.assertIn('.uni-hero-next { display: none; }', self._html())


class HeroPauseTests(TestCase):
    """چرخش در تب پنهان و پایین صفحه، اسلاید را از چشم کاربر می‌برد."""

    def setUp(self):
        cache.clear()
        for index in range(3):
            Slider.objects.create(
                title='اسلاید %d' % index, order=index, is_active=True,
                image='sliders/s%d.jpg' % index)

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_it_stops_when_the_tab_is_hidden(self):
        html = self._html()
        self.assertIn("'visibilitychange'", html)
        self.assertIn('document.hidden', html)

    def test_it_stops_when_the_hero_is_scrolled_away(self):
        html = self._html()
        self.assertIn('IntersectionObserver', html)
        self.assertIn('isIntersecting', html)

    def test_an_old_browser_still_gets_a_moving_slider(self):
        """بدون IntersectionObserver نباید اسلایدر بی‌حرکت بماند."""
        html = self._html()
        self.assertIn('if (watching) { startAuto(); }', html)
        self.assertIn('watching = true', html)

    def test_reduced_motion_stops_the_carousel(self):
        """اسلایدها می‌مانند، فقط خودشان نمی‌روند."""
        html = self._html()
        self.assertIn('prefers-reduced-motion', html)
        self.assertIn('stillness.matches', html)

    def test_hovering_pauses(self):
        html = self._html()
        self.assertIn("heroWrap.addEventListener('mouseenter', stopAuto)", html)
