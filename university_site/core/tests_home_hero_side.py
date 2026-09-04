"""ستون اطلاع‌رسانی کنار اسلایدر، و جای «دسترسی سریع» در صفحه."""
from datetime import date, timedelta

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Event, SiteSettings
from news.models import News


def _news(title, kind='news'):
    return News.objects.create(
        title=title, content='…', news_type=kind, is_published=True,
        published_at=timezone.now())


class HeroSideColumnTests(TestCase):
    """اسلاید تمام‌عرض بود و هیچ خبری بی‌اسکرول دیده نمی‌شد."""

    def setUp(self):
        cache.clear()
        self.settings_row = SiteSettings.objects.create(
            university_name_fa='موسسه')
        _news('اطلاعیهٔ ثبت‌نام', 'announcement')
        _news('خبر افتتاح آزمایشگاه')
        Event.objects.create(
            title='همایش پژوهشی', date=date.today() + timedelta(days=7),
            is_active=True)

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def _column(self):
        """فقط خودِ ستون — نه بقیهٔ صفحه که همان عنوان‌ها را تکرار دارد."""
        return self._html().split('<aside class="hero-side"')[1].split('</aside>')[0]

    def test_the_column_sits_next_to_the_slider(self):
        html = self._html()
        self.assertIn('class="hero-row has-side"', html)
        self.assertIn('hero-side', html)

    def test_it_carries_announcements_news_and_events(self):
        column = self._column()
        self.assertIn('اطلاعیهٔ ثبت‌نام', column)
        self.assertIn('خبر افتتاح آزمایشگاه', column)
        self.assertIn('همایش پژوهشی', column)

    def test_each_row_leads_somewhere(self):
        column = self._column()
        self.assertIn(reverse('news:announcements'), column)
        self.assertIn(reverse('news:list'), column)

    def test_the_admin_can_switch_the_column_off(self):
        self.settings_row.hero_side_enabled = False
        self.settings_row.save(update_fields=['hero_side_enabled'])
        cache.clear()
        html = self._html()
        self.assertNotIn('<aside class="hero-side"', html)
        # نامِ کلاس در شیوه‌نامهٔ همین صفحه هم هست؛ خودِ عنصر مهم است
        self.assertNotIn('class="hero-row has-side"', html)

    def test_the_admin_can_drop_one_list(self):
        self.settings_row.hero_side_show_events = False
        self.settings_row.save(update_fields=['hero_side_show_events'])
        cache.clear()
        column = self._column()
        self.assertNotIn('همایش پژوهشی', column)
        self.assertIn('اطلاعیهٔ ثبت‌نام', column)

    def test_the_row_count_comes_from_the_panel(self):
        for index in range(6):
            _news('اطلاعیه %d' % index, 'announcement')
        self.settings_row.hero_side_count = 2
        self.settings_row.save(update_fields=['hero_side_count'])
        cache.clear()
        block = self._column().split('اطلاعیه‌ها')[1].split('</ul>')[0]
        self.assertEqual(block.count('<li>'), 2)

    def test_the_slider_height_comes_from_the_panel(self):
        self.settings_row.hero_height = 48
        self.settings_row.save(update_fields=['hero_height'])
        cache.clear()
        self.assertIn('--hero-h: 48svh', self._html())

    def test_nothing_to_show_means_no_empty_column(self):
        News.objects.all().delete()
        Event.objects.all().delete()
        cache.clear()
        self.assertNotIn('<aside class="hero-side"', self._html())

    def test_the_panel_offers_every_switch(self):
        from core.admin import SiteSettingsAdmin

        listed = str(SiteSettingsAdmin.fieldsets)
        for field in ('hero_height', 'hero_side_enabled', 'hero_side_width',
                      'hero_side_count', 'hero_side_show_announcements',
                      'hero_side_show_news', 'hero_side_show_events'):
            self.assertIn(field, listed)


class QuickLinksMovedUpTests(TestCase):
    """«دسترسی سریع» یک پله بالاتر رفت: بین تقویم و مزایای تحصیل."""

    def setUp(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه')

    def test_it_sits_between_the_timeline_and_the_features(self):
        html = self.client.get(reverse('core:home')).content.decode()
        timeline = html.index('تقویم آموزشی')
        quick = html.index('دسترسی سریع')
        features = html.index('مزایای تحصیل')
        self.assertLess(timeline, quick)
        self.assertLess(quick, features)


class HeroSidePolishTests(TestCase):
    """تاریخ شمسی، نشان «تازه»، و قابِ عنابی به‌جای کاغذ سفید."""

    def setUp(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه')
        _news('اطلاعیهٔ تازه', 'announcement')
        _news('خبر تازه')

    def _column(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('<aside class="hero-side"')[1].split('</aside>')[0]

    def test_the_date_is_jalali_not_gregorian(self):
        column = self._column()
        year = str(timezone.now().year)
        self.assertNotIn(year, column, 'تاریخ میلادی روی ستون مانده')
        self.assertIn('۱۴', column)

    def test_a_recent_item_is_flagged_as_new(self):
        self.assertIn('تازه', self._column())

    def test_an_old_item_is_not(self):
        News.objects.all().update(
            published_at=timezone.now() - timedelta(days=40))
        cache.clear()
        column = self._column()
        self.assertNotIn('hero-side-new', column)

    def test_each_list_shows_how_many_are_new(self):
        self.assertIn('hero-side-count', self._column())

    def test_the_panel_has_its_own_ground(self):
        from pathlib import Path

        from django.conf import settings as django_settings

        template = (Path(django_settings.BASE_DIR) / 'templates' / 'core' /
                    'home.html').read_text(encoding='utf-8')
        # سلکتور ‎.hero-row.has-side .hero-side‎ هم بالاتر هست
        rule = template.split('%s.hero-side {' % chr(10))[1].split('}')[0]
        self.assertIn('linear-gradient(165deg, #4e1220', rule)
