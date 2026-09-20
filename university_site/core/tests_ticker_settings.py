"""زمان‌بندی نوار فوری، از پنل — نه از دلِ کد.

سه بار برای همین دو عدد یک دیپلوی لازم شد.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Announcement
from core.context_processors import _ticker_timing
from core.models import SiteSettings


def _announce(count):
    Announcement.objects.all().delete()
    for index in range(count):
        Announcement.objects.create(
            title='اطلاعیهٔ %d' % index, content='…', is_active=True,
            is_urgent=True,
            expires_at=timezone.now().date() + timedelta(days=30))


class TheTimingComesFromThePanelTests(TestCase):

    def setUp(self):
        cache.clear()
        SiteSettings.objects.all().delete()

    def _page(self):
        cache.clear()
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_default_matches_what_was_hard_coded(self):
        SiteSettings.objects.create(university_name_fa='موسسه')
        _announce(1)
        self.assertIn('--urgent-secs: 60s', self._page())

    def test_a_slower_number_reaches_the_page(self):
        SiteSettings.objects.create(university_name_fa='موسسه',
                                    ticker_seconds=120)
        _announce(1)
        self.assertIn('--urgent-secs: 120s', self._page())

    def test_more_items_still_take_longer(self):
        SiteSettings.objects.create(university_name_fa='موسسه',
                                    ticker_seconds=30)
        _announce(3)
        self.assertIn('--urgent-secs: 90s', self._page())

    def test_the_pause_is_written_in_seconds_not_percent(self):
        """موسسه ثانیه می‌نویسد؛ درصد کار CSS است، نه کار مدیر سایت."""
        SiteSettings.objects.create(university_name_fa='موسسه',
                                    ticker_seconds=90,
                                    ticker_hold_seconds=10)
        _announce(1)
        html = self._page()
        self.assertIn('10% { transform: translateX(-50%); }', html)

    def test_the_pause_follows_the_speed(self):
        """۲ ثانیه از ۶۰ می‌شود ۳٪، و از ۲۰۰ می‌شود ۱٪."""
        row = SiteSettings.objects.create(university_name_fa='موسسه',
                                          ticker_hold_seconds=2)
        _announce(1)
        self.assertEqual(_ticker_timing(row, [1])['urgent_hold_percent'], 3)
        row.ticker_seconds = 200
        self.assertEqual(_ticker_timing(row, [1])['urgent_hold_percent'], 1)

    def test_no_pause_when_asked_for_none(self):
        row = SiteSettings.objects.create(university_name_fa='موسسه',
                                          ticker_hold_seconds=0)
        self.assertEqual(_ticker_timing(row, [1])['urgent_hold_percent'], 0)

    def test_a_silly_pause_cannot_swallow_the_whole_run(self):
        """مکث بلندتر از حرکت یعنی نوار ایستاده."""
        row = SiteSettings.objects.create(university_name_fa='موسسه',
                                          ticker_seconds=10,
                                          ticker_hold_seconds=60)
        self.assertLessEqual(_ticker_timing(row, [1])['urgent_hold_percent'],
                             40)

    def test_the_pause_is_added_to_the_run_not_taken_from_it(self):
        """موسسه هر دو عدد را روی یک گذاشت و عبور شد نیم‌ثانیه.

        مکث از همان یک ثانیه کم می‌شد، پس «زمان هر خبر» دیگر زمانِ
        عبور نبود. حالا عبور همیشه همان عددی است که نوشته‌اند.
        """
        row = SiteSettings.objects.create(university_name_fa='موسسه',
                                          ticker_seconds=40,
                                          ticker_hold_seconds=10)
        timing = _ticker_timing(row, [1])
        self.assertEqual(timing['urgent_total_secs'], 50)
        # ۱۰ ثانیه از ۵۰ یعنی یک‌پنجم؛ ۴۰ ثانیهٔ عبور دست‌نخورده
        self.assertEqual(timing['urgent_hold_percent'], 20)

    def test_the_travel_time_is_what_the_panel_says(self):
        """هر مکثی که باشد، عبور همان عدد است."""
        row = SiteSettings.objects.create(university_name_fa='موسسه',
                                          ticker_seconds=30)
        for hold in (0, 1, 5, 20):
            row.ticker_hold_seconds = hold
            timing = _ticker_timing(row, [1])
            travel = (timing['urgent_total_secs']
                      * (100 - timing['urgent_hold_percent']) / 100.0)
            self.assertAlmostEqual(travel, 30, delta=1,
                                   msg='با مکث %d ثانیه عبور %s شد' % (
                                       hold, travel))

    def test_a_fresh_database_still_renders(self):
        """هنوز ردیف تنظیماتی نیست."""
        self.assertFalse(SiteSettings.objects.exists())
        _announce(1)
        self.assertIn('--urgent-secs: 60s', self._page())

    def test_the_keyframes_beat_the_stylesheet(self):
        """تعریف درون صفحه بعد از main.css می‌آید، پس همان می‌نشیند."""
        SiteSettings.objects.create(university_name_fa='موسسه')
        _announce(1)
        html = self._page()
        self.assertLess(html.index('main.css'), html.index('@keyframes urgentSlide'))


class ThePanelShowsBothBoxesTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'modirticker', 't@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.staff)
        self.row = SiteSettings.objects.create(university_name_fa='موسسه')

    def test_both_fields_are_on_the_form(self):
        html = self.client.get(
            '/admin/core/sitesettings/%d/change/' % self.row.pk
        ).content.decode()
        self.assertIn('name="ticker_seconds"', html)
        self.assertIn('name="ticker_hold_seconds"', html)

    def test_they_sit_in_their_own_section(self):
        from core.admin import SiteSettingsAdmin

        self.assertIn('نوار خبر فوری', str(SiteSettingsAdmin.fieldsets))

    def test_a_very_fast_speed_is_allowed(self):
        """کفِ پنج ثانیه حدسِ ما بود و سرِ راهِ تنظیم سرعت ایستاد.

        موسسه پیغام «مطمئن شوید این مقدار بزرگ‌تر یا مساوی ۵ است»
        می‌گرفت و نمی‌توانست تندش کند.
        """
        self.row.ticker_seconds = 1
        self.row.full_clean()

    def test_an_absurd_speed_is_still_refused(self):
        from django.core.exceptions import ValidationError

        self.row.ticker_seconds = 0
        with self.assertRaises(ValidationError):
            self.row.full_clean()

    def test_a_sensible_speed_is_accepted(self):
        self.row.ticker_seconds = 90
        self.row.ticker_hold_seconds = 4
        self.row.full_clean()

    def _form(self):
        from django.contrib.admin.sites import site

        return site._registry[SiteSettings].get_form(
            self._request(), self.row, change=True)

    def _request(self):
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        request.user = self.staff
        return request

    def test_the_number_boxes_are_not_html_number_inputs(self):
        """ورودی \u200Etype="number"\u200E رقم فارسی را دور می‌ریخت.

        مدیر سایت «۱» می‌نوشت، مرورگر خالی می‌فرستاد، و فرم می‌گفت
        این فیلد لازم است — یعنی عدد اصلاً ذخیره نمی‌شد.
        """
        html = self.client.get(
            '/admin/core/sitesettings/%d/change/' % self.row.pk
        ).content.decode()
        box = html.split('name="ticker_hold_seconds"')[0][-400:]
        self.assertNotIn('type="number"', box)

    def test_a_persian_one_is_saved_as_one(self):
        form = self._form()(
            {'ticker_hold_seconds': '۱'}, instance=self.row)
        form.is_valid()
        self.assertNotIn('ticker_hold_seconds', form.errors)
        self.assertEqual(form.cleaned_data['ticker_hold_seconds'], 1)

    def test_a_persian_zero_is_saved_as_zero(self):
        """صفر یعنی بی‌مکث؛ پیش از این «لازم است» می‌گرفت."""
        form = self._form()(
            {'ticker_hold_seconds': '۰'}, instance=self.row)
        form.is_valid()
        self.assertEqual(form.cleaned_data['ticker_hold_seconds'], 0)

    def test_a_latin_one_still_works(self):
        form = self._form()({'ticker_hold_seconds': '1'}, instance=self.row)
        form.is_valid()
        self.assertEqual(form.cleaned_data['ticker_hold_seconds'], 1)

    def test_one_second_reaches_the_page(self):
        """عدد ۱ باید واقعاً روی صفحه اثر بگذارد، نه فقط ذخیره شود."""
        self.row.ticker_seconds = 50
        self.row.ticker_hold_seconds = 1
        self.assertEqual(_ticker_timing(self.row, [1])['urgent_hold_percent'],
                         2)
