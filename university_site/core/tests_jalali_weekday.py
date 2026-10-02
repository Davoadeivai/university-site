"""نام روز هفته باید با خودِ تاریخ بخواند، و «امروز» یعنی امروزِ تهران.

دو خطا بود:
* فهرست روزها از دوشنبه شروع می‌شد ولی jdatetime شنبه را صفر می‌شمارد؛
  جمعه «یکشنبه» نوشته می‌شد — دو روز جابه‌جا.
* timezone.now().date() تاریخ UTC است؛ از نیمه‌شب تا ۳:۳۰ بامداد تهران
  صفحهٔ اول تاریخ دیروز را نشان می‌داد.
"""
from datetime import date, datetime, timezone as dt_timezone
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from core.jalali import format_jalali_date


class TheWeekdayMatchesTheDateTests(TestCase):

    def test_each_day_of_one_week(self):
        week = {
            date(2026, 10, 3): 'شنبه ۱۱ مهر ۱۴۰۵',
            date(2026, 10, 4): 'یکشنبه ۱۲ مهر ۱۴۰۵',
            date(2026, 10, 5): 'دوشنبه ۱۳ مهر ۱۴۰۵',
            date(2026, 10, 6): 'سه‌شنبه ۱۴ مهر ۱۴۰۵',
            date(2026, 10, 7): 'چهارشنبه ۱۵ مهر ۱۴۰۵',
            date(2026, 10, 8): 'پنج‌شنبه ۱۶ مهر ۱۴۰۵',
            date(2026, 10, 9): 'جمعه ۱۷ مهر ۱۴۰۵',
        }
        for day, expected in week.items():
            self.assertEqual(format_jalali_date(day, 'full'), expected, day)

    def test_nowruz(self):
        self.assertEqual(format_jalali_date(date(2026, 3, 21), 'full'),
                         'شنبه ۱ فروردین ۱۴۰۵')


class TodayIsTehransTodayTests(TestCase):

    def test_half_past_midnight_in_tehran_is_already_the_next_day(self):
        # ۲۱:۰۰ UTC پنج‌شنبه = ۰۰:۳۰ بامداد جمعه در تهران
        utc = datetime(2026, 10, 1, 21, 0, tzinfo=dt_timezone.utc)
        with mock.patch('django.utils.timezone.now', return_value=utc):
            response = self.client.get('/')
        # همان مقداری که سربرگ ستون خبرها با jalali_date:"full" نشان می‌دهد
        self.assertEqual(response.context['today'], date(2026, 10, 2))
        self.assertEqual(format_jalali_date(response.context['today'], 'full'),
                         'جمعه ۱۰ مهر ۱۴۰۵')
