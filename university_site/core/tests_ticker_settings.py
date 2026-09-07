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
                                    ticker_seconds=100,
                                    ticker_hold_seconds=10)
        _announce(1)
        html = self._page()
        self.assertIn('0%, 10% { left: 0; }', html)

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
                             50)

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

    def test_an_absurd_speed_is_refused(self):
        from django.core.exceptions import ValidationError

        self.row.ticker_seconds = 1
        with self.assertRaises(ValidationError):
            self.row.full_clean()

    def test_a_sensible_speed_is_accepted(self):
        self.row.ticker_seconds = 90
        self.row.ticker_hold_seconds = 4
        self.row.full_clean()
