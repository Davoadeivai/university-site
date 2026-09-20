"""ستون کنار اسلایدر: سربرگ «پایگاه خبری» و شمارش معکوس رویدادها."""
from datetime import date, timedelta

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Event, SiteSettings
from news.models import News


class NewsdeskMastheadTests(TestCase):
    """ستون سه فهرست داشت و هیچ نامی — کنار اسلاید یک تکه فهرست بود."""

    def setUp(self):
        cache.clear()
        self.settings_row = SiteSettings.objects.create(
            university_name_fa='موسسه آموزش عالی علامه امینی')
        News.objects.create(title='خبر نمونه', content='…', summary='…',
                            is_published=True)

    def _html(self):
        cache.clear()
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_column_is_titled(self):
        html = self._html()
        self.assertIn('پایگاه خبری', html)
        self.assertIn('id="newsdeskTitle"', html)

    def test_the_title_comes_from_the_panel(self):
        self.settings_row.hero_side_title = 'اتاق خبر'
        self.settings_row.save()
        self.assertIn('اتاق خبر', self._html())

    def test_an_empty_title_falls_back(self):
        self.settings_row.hero_side_title = ''
        self.settings_row.save()
        self.assertIn('پایگاه خبری', self._html())

    def test_the_tagline_is_the_institute_by_default(self):
        self.assertIn('موسسه آموزش عالی علامه امینی', self._html())

    def test_the_tagline_comes_from_the_panel(self):
        self.settings_row.hero_side_tagline = 'صدای دانشگاه'
        self.settings_row.save()
        self.assertIn('صدای دانشگاه', self._html())

    def test_todays_date_is_jalali_not_gregorian(self):
        from core.jalali import format_jalali_date

        html = self._html()
        self.assertIn(format_jalali_date(timezone.now().date(), 'full'), html)
        self.assertNotIn(str(timezone.now().year), html.split('newsdesk-sub')[1][:400])

    def test_the_column_is_labelled_by_its_own_heading(self):
        self.assertIn('aria-labelledby="newsdeskTitle"', self._html())

    def test_no_masthead_when_the_column_is_off(self):
        """سربرگ با ستون می‌آید و با ستون می‌رود."""
        self.settings_row.hero_side_enabled = False
        self.settings_row.save()
        self.assertNotIn('id="newsdeskTitle"', self._html())


class EventCountdownTests(TestCase):
    """«۱۴۰۵/۰۶/۱۶» را باید با امروز سنجید تا معلوم شود نزدیک است."""

    def setUp(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه')

    def _html(self):
        cache.clear()
        return self.client.get(reverse('core:home')).content.decode()

    def _event(self, days):
        return Event.objects.create(
            title='همایش', date=date.today() + timedelta(days=days),
            is_active=True)

    def test_today_is_named_today(self):
        self._event(0)
        self.assertIn('امروز', self._html())

    def test_tomorrow_is_named_tomorrow(self):
        self._event(1)
        self.assertIn('فردا', self._html())

    def test_a_few_days_off_is_counted(self):
        self._event(3)
        self.assertIn('۳ روز مانده', self._html())

    def test_a_distant_event_gets_no_chip(self):
        self._event(40)
        self.assertNotIn('روز مانده', self._html())

    def test_the_date_is_still_shown(self):
        from core.jalali import format_jalali_date

        row = self._event(3)
        self.assertIn(format_jalali_date(row.date, 'short'), self._html())


class TheFeedIsGoneTests(TestCase):
    """خوراک خبری (RSS/Atom) به خواست موسسه کامل برداشته شد.

    سالی که روی سایت بود نه کسی مشترکش شد و نه جایی نشان داده
    می‌شد. این تست‌ها می‌مانند تا اگر روزی بی‌سبب برگشت، معلوم شود.
    """

    def test_no_route_is_left_behind(self):
        from django.urls import NoReverseMatch

        for name in ('news:feed', 'news:feed_atom'):
            with self.assertRaises(NoReverseMatch):
                reverse(name)

    def test_the_old_addresses_are_not_served(self):
        for path in ('/اخبار/rss/', '/اخبار/atom/'):
            self.assertEqual(self.client.get(path).status_code, 404,
                             'هنوز پاسخ می‌دهد: %s' % path)

    def test_the_browser_is_no_longer_told_about_it(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('application/rss+xml', html)
        self.assertNotIn('application/atom+xml', html)

    def test_the_button_is_gone_from_the_first_page(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('newsdesk-rss', html)
        self.assertNotIn('fa-rss', html)

    def test_the_news_page_itself_still_works(self):
        """برداشتن خوراک نباید به خودِ اخبار دست بزند."""
        News.objects.create(title='خبر تازه', content='متن',
                            summary='خلاصه', is_published=True)
        body = self.client.get(reverse('news:list')).content.decode()
        self.assertIn('خبر تازه', body)
