"""تست‌های هویت بصری و تقویم آموزشی.

اجرا:  python manage.py test core
"""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from academics.models import AcademicCalendar
from core.academic_timeline import build_timeline

INSTITUTE = 'موسسه آموزش عالی علامه امینی'
OLD_NAME = 'علامه امینی بهنمیر'


class BrandNameTests(TestCase):
    """نام موسسه دیگر «بهنمیر» ندارد و در بنر متن زنده است."""

    def test_home_uses_new_name_only(self):
        res = self.client.get(reverse('core:home'))
        body = res.content.decode()
        self.assertEqual(res.status_code, 200)
        self.assertIn(INSTITUTE, body)
        self.assertNotIn(OLD_NAME, body)

    def test_banner_is_live_text_not_an_image(self):
        body = self.client.get(reverse('core:home')).content.decode()
        # نام باید متن باشد تا سئو و screen reader بخوانندش
        self.assertIn('class="bnr-fa"', body)
        # بنر تصویری قدیمی که نام داخلش پخته بود
        self.assertNotIn('banner-complete-786x86.png', body)
        # نشان‌ها دارایی جدا هستند
        self.assertIn('mark-institute.png', body)
        self.assertIn('mark-iran.png', body)

    def test_login_page_uses_new_name(self):
        body = self.client.get(reverse('accounts:login')).content.decode()
        self.assertNotIn(OLD_NAME, body)


class AcademicTimelineTests(TestCase):
    """وضعیت زندهٔ مراحل — چیزی که یک تصویر ثابت نمی‌تواند بدهد."""

    def setUp(self):
        self.today = timezone.localdate()
        self.year = '1405-1406'
        mk = AcademicCalendar.objects.create
        mk(title='گذشته', academic_year=self.year, semester='fall',
           start_date=self.today - timedelta(days=30),
           end_date=self.today - timedelta(days=25))
        mk(title='در جریان', academic_year=self.year, semester='fall',
           start_date=self.today - timedelta(days=2),
           end_date=self.today + timedelta(days=2))
        mk(title='بعدی', academic_year=self.year, semester='fall',
           start_date=self.today + timedelta(days=10),
           end_date=self.today + timedelta(days=10))
        mk(title='دورتر', academic_year=self.year, semester='fall',
           start_date=self.today + timedelta(days=40),
           end_date=self.today + timedelta(days=40))

    def _states(self):
        return {n['title']: n['state'] for n in build_timeline()['nodes']}

    def test_states_are_assigned_correctly(self):
        s = self._states()
        self.assertEqual(s['گذشته'], 'past')
        self.assertEqual(s['در جریان'], 'now')
        self.assertEqual(s['بعدی'], 'next')
        self.assertEqual(s['دورتر'], 'future')

    def test_only_one_milestone_is_next(self):
        nodes = build_timeline()['nodes']
        self.assertEqual(sum(1 for n in nodes if n['state'] == 'next'), 1)

    def test_days_left_only_on_next(self):
        nodes = {n['title']: n for n in build_timeline()['nodes']}
        self.assertEqual(nodes['بعدی']['days_left'], 10)
        self.assertIsNone(nodes['گذشته']['days_left'])
        self.assertIsNone(nodes['در جریان']['days_left'])

    def test_empty_calendar_is_handled(self):
        AcademicCalendar.objects.all().delete()
        t = build_timeline()
        self.assertFalse(t['has_data'])
        self.assertEqual(t['nodes'], [])
        # صفحه اصلی نباید بشکند
        self.assertEqual(self.client.get(reverse('core:home')).status_code, 200)

    def test_timeline_renders_on_home(self):
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('class="acal"', body)
        self.assertIn('در جریان', body)
        self.assertIn('روز دیگر', body)

    def test_current_semester_is_chosen_over_others(self):
        """اگر چند سال تحصیلی باشد، سالی که امروز داخلش است انتخاب می‌شود."""
        AcademicCalendar.objects.create(
            title='سال قدیم', academic_year='1400-1401', semester='fall',
            start_date=self.today - timedelta(days=900),
            end_date=self.today - timedelta(days=800))
        t = build_timeline()
        self.assertEqual(t['academic_year'], self.year)
        self.assertNotIn('سال قدیم', [n['title'] for n in t['nodes']])


class TimelineClickTargetTests(TestCase):
    """هر مرحلهٔ تایم‌لاین به یک صفحهٔ واقعی پنل دانشجو لینک می‌شود."""

    def setUp(self):
        self.today = timezone.localdate()

    def _mk(self, **kw):
        base = dict(
            title='مرحله', academic_year='1405-1406', semester='fall',
            start_date=self.today, end_date=self.today,
        )
        base.update(kw)
        return AcademicCalendar.objects.create(**base)

    def test_action_resolves_to_real_url(self):
        item = self._mk(title='انتخاب واحد', action='registration')
        self.assertEqual(item.get_action_url(), reverse('dashboard:student_registration'))

    def test_every_action_choice_resolves(self):
        """هیچ گزینه‌ای در پنل نباید به آدرس شکسته منتهی شود."""
        broken = []
        for key, _label in AcademicCalendar.ACTION_CHOICES:
            if key in ('', 'external'):
                continue
            item = self._mk(title=f'x-{key}', action=key)
            if not item.get_action_url():
                broken.append(key)
        self.assertEqual(broken, [], f'این اقدام‌ها آدرس ندارند: {broken}')

    def test_external_url_is_used_when_selected(self):
        item = self._mk(action='external', external_url='https://example.org/x')
        self.assertEqual(item.get_action_url(), 'https://example.org/x')

    def test_no_action_means_no_link(self):
        self.assertEqual(self._mk(action='').get_action_url(), '')

    def test_icon_falls_back_to_action_default(self):
        self.assertEqual(self._mk(action='grades').display_icon, 'fa-award')
        self.assertEqual(self._mk(action='grades', icon='fa-star').display_icon, 'fa-star')

    def test_inactive_milestones_are_hidden(self):
        self._mk(title='پنهان', action='grades', is_active=False)
        self._mk(title='نمایان', action='grades', is_active=True)
        titles = [n['title'] for n in build_timeline()['nodes']]
        self.assertIn('نمایان', titles)
        self.assertNotIn('پنهان', titles)

    def test_order_overrides_date(self):
        self._mk(title='دوم', order=2, start_date=self.today,
                 end_date=self.today)
        self._mk(title='اول', order=1,
                 start_date=self.today + timedelta(days=5),
                 end_date=self.today + timedelta(days=5))
        titles = [n['title'] for n in build_timeline()['nodes']]
        self.assertEqual(titles[:2], ['اول', 'دوم'])

    def test_card_renders_as_link_on_home(self):
        self._mk(title='انتخاب واحد', action='registration',
                 start_date=self.today + timedelta(days=3),
                 end_date=self.today + timedelta(days=3))
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn(reverse('dashboard:student_registration'), body)
        self.assertIn('acal-card', body)
        self.assertIn('acal-cap', body)   # نیم‌دایره


class HomeSectionTests(TestCase):
    """هر بخش صفحهٔ اصلی از پنل تصویر و عنوان می‌گیرد و پنهان‌شدنی است."""

    def test_home_renders_without_any_section_record(self):
        from core.models import HomeSection
        HomeSection.objects.all().delete()
        res = self.client.get(reverse('core:home'))
        self.assertEqual(res.status_code, 200)

    def test_custom_title_replaces_default(self):
        from core.models import HomeSection
        HomeSection.objects.update_or_create(
            key='features', defaults={'title': 'چرا اینجا؟', 'is_visible': True})
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('چرا اینجا؟', body)

    def test_hiding_a_section_removes_it(self):
        from core.models import HomeFeature, HomeSection
        HomeFeature.objects.create(title='مزیت آزمایشی', icon='fa-star')
        HomeSection.objects.update_or_create(
            key='features', defaults={'is_visible': True})
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('مزیت آزمایشی', body)

        HomeSection.objects.filter(key='features').update(is_visible=False)
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('مزیت آزمایشی', body)

    def test_features_come_from_database(self):
        from core.models import HomeFeature
        HomeFeature.objects.all().delete()
        feature = HomeFeature.objects.create(title='مزیت یکتا', description='توضیح',
                                             icon='fa-flask', tone='green', order=1)
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('مزیت یکتا', body)
        self.assertIn('fa-flask', body)
        # رنگ از مدل می‌آید نه از قالب — هگز را از خود مدل بخوان تا تست با
        # هر بار عوض‌شدن پالت نشکند
        self.assertIn(feature.color, body)

    def test_inactive_feature_is_hidden(self):
        from core.models import HomeFeature
        HomeFeature.objects.create(title='غیرفعال', icon='fa-star', is_active=False)
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('غیرفعال', body)
