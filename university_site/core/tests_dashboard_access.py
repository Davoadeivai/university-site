"""داشبورد ادمین: درهای همیشگی، و کارهایی که کسی گزارششان نمی‌دهد."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicGroup, Department, Major
from core.admin_search import build_work_queue
from core.models import Council
from core.templatetags.admin_dashboard import ESSENTIAL_LINKS, _essential_links
from news.models import News


class EssentialLinksTests(TestCase):
    """کارِ روزمرهٔ مدیر سایت نباید از جست‌وجو شروع شود."""

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'modir', 'modir@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.staff)

    def _dashboard(self):
        return self.client.get(reverse('admin:index')).content.decode()

    def test_every_listed_door_resolves(self):
        rows = _essential_links()
        self.assertEqual(len(rows), len(ESSENTIAL_LINKS))
        for row in rows:
            self.assertTrue(row['url'].startswith('/admin/'), row)

    def test_they_are_shown_on_the_dashboard(self):
        html = self._dashboard()
        self.assertIn('admin-essentials', html)
        for label in ('تنظیمات سایت', 'اخبار', 'شوراها', 'افراد موسسه',
                      'گزارش فعالیت ادمین'):
            self.assertIn(label, html)

    def test_each_door_actually_opens(self):
        for row in _essential_links():
            response = self.client.get(row['url'])
            self.assertEqual(response.status_code, 200, row['label'])

    def test_a_visitor_sees_none_of_it(self):
        self.client.logout()
        response = self.client.get(reverse('admin:index'))
        self.assertNotEqual(response.status_code, 200)


class ContentHealthQueueTests(TestCase):
    """صف کار فقط کارِ مردم را می‌شمرد، نه کارِ خودِ سایت."""

    def setUp(self):
        self.faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-dash', order=1, is_active=True)

    def _queue(self):
        return {item['key']: item for item in build_work_queue()}

    def test_a_group_without_a_head_is_counted(self):
        AcademicGroup.objects.create(
            department=self.faculty, name='گروه بی‌مدیر', slug='bi-modir',
            is_active=True)
        self.assertEqual(self._queue()['groups_without_head']['count'], 1)

    def test_a_group_with_a_head_is_not(self):
        AcademicGroup.objects.create(
            department=self.faculty, name='گروه بامدیر', slug='ba-modir',
            is_active=True, head='دکتر نمونه')
        self.assertEqual(self._queue()['groups_without_head']['count'], 0)

    def test_a_major_without_a_curriculum_is_counted(self):
        Major.objects.create(
            department=self.faculty, name='رشتهٔ بی‌سرفصل', slug='bi-sarfasl',
            degree='master', is_active=True)
        self.assertEqual(
            self._queue()['majors_without_curriculum']['count'], 1)

    def test_a_major_with_text_curriculum_is_not(self):
        Major.objects.create(
            department=self.faculty, name='رشتهٔ باسرفصل', slug='ba-sarfasl',
            degree='master', is_active=True, curriculum='درس یکم')
        self.assertEqual(
            self._queue()['majors_without_curriculum']['count'], 0)

    def test_an_unpublished_news_item_is_counted(self):
        News.objects.create(title='پیش‌نویس', content='…', is_published=False)
        self.assertEqual(self._queue()['news_drafts']['count'], 1)

    def test_a_council_without_members_is_counted(self):
        Council.objects.create(
            name='شورای خالی', slug='khali-dash', is_active=True)
        self.assertEqual(
            self._queue()['councils_without_members']['count'], 1)

    def test_every_row_carries_a_link(self):
        for item in build_work_queue():
            self.assertTrue(item['url'], item['key'])

    def test_nothing_pending_means_a_clean_queue(self):
        total = sum(item['count'] for item in build_work_queue())
        self.assertEqual(total, 0)


class DashboardIsNotClutteredTests(TestCase):
    """هشتاد و یک بخش، همه باز، یعنی صفحه‌ای به بلندی چند نمایشگر."""

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'modir2', 'modir2@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.staff)

    def _dashboard(self):
        return self.client.get(reverse('admin:index')).content.decode()

    def test_groups_are_collapsed_not_stacked(self):
        html = self._dashboard()
        self.assertIn('admin-section-summary', html)
        self.assertIn('<details class="admin-section-block"', html)

    def test_only_the_first_group_starts_open(self):
        import re

        html = self._dashboard()
        blocks = re.findall(r'<details class="admin-section-block"[^>]*>', html)
        self.assertGreater(len(blocks), 1)
        opened = [block for block in blocks if ' open' in block]
        self.assertEqual(len(opened), 1)

    def test_the_technical_models_are_out_of_the_menu(self):
        from django.conf import settings as django_settings

        hidden = django_settings.JAZZMIN_SETTINGS['hide_models']
        for key in ('core.QueuedSMS', 'accounts.OTPCode',
                    'admissions.AdmissionOTP', 'core.PageView'):
            self.assertIn(key, hidden)

    def test_they_are_hidden_not_removed(self):
        """پنهان یعنی از منو، نه از دسترس."""
        for url in ('/admin/core/queuedsms/', '/admin/accounts/otpcode/'):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_the_top_menu_holds_four_daily_jobs(self):
        from django.conf import settings as django_settings

        links = django_settings.JAZZMIN_SETTINGS['topmenu_links']
        self.assertEqual(len(links), 4)


class ContentPulseTests(TestCase):
    """داشبورد نمی‌گفت سایت اصلاً چه دارد."""

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'modir3', 'modir3@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.staff)

    def test_the_numbers_are_shown(self):
        from core.templatetags.admin_dashboard import _content_stats

        rows = _content_stats()
        self.assertGreaterEqual(len(rows), 5)
        html = self.client.get(reverse('admin:index')).content.decode()
        self.assertIn('admin-pulse-card', html)

    def test_each_number_is_a_door(self):
        from core.templatetags.admin_dashboard import _content_stats

        for row in _content_stats():
            self.assertTrue(row['url'].startswith('/admin/'), row)
            self.assertEqual(
                self.client.get(row['url']).status_code, 200, row['label'])

    def test_the_counts_are_real(self):
        from academics.models import Department
        from core.templatetags.admin_dashboard import _content_stats

        Department.objects.create(name='دانشکدهٔ شمارش', slug='shomaresh',
                                  is_active=True)
        rows = {row['label']: row['count'] for row in _content_stats()}
        self.assertEqual(rows['دانشکده'], 1)
