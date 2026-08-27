"""ایرادهایی که بازرسی سراسری سایت پیدا کرد."""
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from academics.models import Department


class TransportSecurityTests(TestCase):
    """کوکی نشست روی http هم فرستاده می‌شد و در مسیر قابل شنود بود."""

    def _production(self):
        """تنظیم‌ها را همان‌طور که با DEBUG=False می‌شوند بخوان."""
        import importlib
        import os

        previous = os.environ.get('DEBUG')
        os.environ['DEBUG'] = 'False'
        try:
            module = importlib.import_module('config.settings')
            return importlib.reload(module)
        finally:
            if previous is None:
                os.environ.pop('DEBUG', None)
            else:
                os.environ['DEBUG'] = previous
            importlib.reload(module)

    def test_cookies_are_https_only_in_production(self):
        settings_module = self._production()
        self.assertTrue(settings_module.SESSION_COOKIE_SECURE)
        self.assertTrue(settings_module.CSRF_COOKIE_SECURE)

    def test_cookies_are_hidden_from_javascript(self):
        settings_module = self._production()
        self.assertTrue(settings_module.SESSION_COOKIE_HTTPONLY)

    def test_content_type_sniffing_is_off(self):
        self.assertTrue(self._production().SECURE_CONTENT_TYPE_NOSNIFF)

    def test_django_can_tell_the_request_came_over_https(self):
        """پشت Passenger بدون این سرآیند، هر بررسی امنیتی کور است."""
        from django.conf import settings

        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER,
                         ('HTTP_X_FORWARDED_PROTO', 'https'))

    def test_the_https_redirect_stays_off_by_default(self):
        """وب‌سرور خودش ریدایرکت می‌کند؛ روشن‌بودنش حلقه می‌سازد."""
        from django.conf import settings

        self.assertFalse(settings.SECURE_SSL_REDIRECT)

    def test_hsts_is_off_until_someone_chooses_it(self):
        """HSTS برگشت‌پذیر نیست — نباید بی‌خبر روشن شود."""
        from django.conf import settings

        self.assertEqual(settings.SECURE_HSTS_SECONDS, 0)

    def test_local_development_is_not_forced_onto_https(self):
        from django.conf import settings

        if settings.DEBUG:
            self.assertFalse(getattr(settings, 'SESSION_COOKIE_SECURE', False))


class HomeFacultyListTests(TestCase):
    """فهرست دانشکده‌های صفحهٔ اصلی باید با منوی بالا یکی باشد."""

    def setUp(self):
        cache.clear()
        for index in range(7):
            Department.objects.create(
                name='دانشکده %d' % index, slug='d%d' % index,
                order=index, is_active=True)

    def _home(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_a_seventh_faculty_is_not_dropped(self):
        """با سقف ۶، دانشکدهٔ هفتم در منو بود و در صفحهٔ اصلی نبود."""
        html = self._home().split('fac-grid')[1].split('</section>')[0]
        for index in range(7):
            self.assertIn('دانشکده %d' % index, html)

    def test_the_order_matches_the_faculties_page(self):
        home = self._home().split('fac-grid')[1].split('</section>')[0]
        page = self.client.get(
            reverse('academics:departments')).content.decode()
        tree = page.split('<div class="trunk">')[1]
        first = [n for n in range(7) if 'دانشکده %d' % n in home]
        self.assertEqual(
            first, sorted(first, key=lambda n: home.index('دانشکده %d' % n)))
        self.assertEqual(
            first, sorted(first, key=lambda n: tree.index('دانشکده %d' % n)))

    def test_an_inactive_faculty_is_on_neither(self):
        Department.objects.filter(order=0).update(is_active=False)
        cache.clear()
        home = self._home().split('fac-grid')[1].split('</section>')[0]
        self.assertNotIn('دانشکده 0', home)


class CurriculumDeadLinkTests(TestCase):
    """کارت سرفصل، دانلودی را تبلیغ می‌کرد که ۴۰۴ می‌داد."""

    def setUp(self):
        cache.clear()
        from directory.models import CurriculumDocument

        self.model = CurriculumDocument
        self.missing = CurriculumDocument.objects.create(
            title='سرفصل بی‌فایل', level='bachelor_cont',
            file='curricula/gone.pdf', is_active=True)

    def _html(self):
        return self.client.get(reverse('directory:curricula')).content.decode()

    def test_a_missing_file_is_not_offered_for_download(self):
        html = self._html()
        self.assertIn('سرفصل بی‌فایل', html)
        self.assertNotIn(
            reverse('directory:curriculum_download', args=[self.missing.pk]),
            html)

    def test_it_says_why_instead_of_going_quiet(self):
        self.assertIn('هنوز بارگذاری نشده', self._html())

    def test_the_card_is_marked_as_pending(self):
        self.assertIn('is-pending', self._html())

    def test_a_visitor_is_not_told_to_open_the_panel(self):
        """آدرس پنل به کار بازدیدکننده نمی‌آید."""
        self.assertNotIn('روی سرور نیست', self._html())

    def test_staff_are_told_how_many_are_missing(self):
        from django.contrib.auth import get_user_model

        staff = get_user_model().objects.create_user(
            username='karmand', password='x', is_staff=True)
        self.client.force_login(staff)
        cache.clear()
        html = self._html()
        self.assertIn('روی سرور نیست', html)
        self.assertIn('/admin/directory/curriculumdocument/', html)

    def test_the_download_view_still_refuses_a_missing_file(self):
        """قالب دیگر لینک نمی‌دهد، ولی نشانی مستقیم هم نباید بترکد."""
        response = self.client.get(
            reverse('directory:curriculum_download', args=[self.missing.pk]))
        self.assertEqual(response.status_code, 404)


class MissingDocumentTests(TestCase):
    """نام فایل در دیتابیس، دلیل بودنش روی دیسک نیست."""

    def setUp(self):
        cache.clear()
        from core.models import DownloadableDocument

        self.doc = DownloadableDocument.objects.create(
            title='آیین‌نامهٔ بی‌فایل', file='documents/gone.pdf',
            degree_level='bachelor_continuous', category='regulation',
            is_active=True)

    def test_a_recorded_but_absent_file_reads_as_absent(self):
        self.assertFalse(self.doc.has_file)

    def test_an_empty_field_reads_as_absent(self):
        from core.models import DownloadableDocument

        empty = DownloadableDocument(title='خالی')
        self.assertFalse(empty.has_file)
        self.assertFalse(empty.has_word)

    def test_the_download_url_does_not_point_at_a_404(self):
        self.assertEqual(self.doc.download_url, '')

    def test_an_external_link_is_used_when_the_file_is_gone(self):
        self.doc.external_url = 'https://example.org/a.pdf'
        self.doc.save(update_fields=['external_url'])
        self.assertEqual(self.doc.download_url, 'https://example.org/a.pdf')

    def test_the_detail_page_does_not_frame_a_missing_pdf(self):
        response = self.client.get(
            reverse('core:document_detail', args=[self.doc.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('documents/gone.pdf', response.content.decode())

    def test_the_list_does_not_promise_a_pdf(self):
        """نشان «PDF» کنار سندی که فایلش نیست، وعدهٔ بی‌پشتوانه است."""
        html = self.client.get(
            reverse('core:documents'),
            {'degree': self.doc.degree_level},
        ).content.decode()
        self.assertIn('آیین‌نامهٔ بی‌فایل', html)
        block = html.split('آیین‌نامهٔ بی‌فایل')[1][:500]
        self.assertNotIn('PDF', block)


class MissingMediaReportTests(TestCase):
    """مدیر باید بداند کدام فایل‌ها هنوز روی سرور نیستند."""

    def _run(self, *args):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('check_media_files', *args, stdout=out)
        return out.getvalue()

    def test_a_clean_database_says_so(self):
        self.assertIn('روی سرور هستند', self._run())

    def test_a_missing_file_is_counted(self):
        from core.models import DownloadableDocument

        DownloadableDocument.objects.create(
            title='گمشده', file='documents/gone.pdf',
            degree_level='bachelor_continuous', category='form', is_active=True)
        output = self._run()
        self.assertIn('روی سرور نیست', output)
        self.assertIn('file', output)

    def test_list_names_the_files(self):
        from core.models import DownloadableDocument

        DownloadableDocument.objects.create(
            title='گمشده', file='documents/gone.pdf',
            degree_level='bachelor_continuous', category='form', is_active=True)
        self.assertIn('documents/gone.pdf', self._run('--list'))

    def test_it_says_why_the_deploy_will_not_fix_it(self):
        from core.models import DownloadableDocument

        DownloadableDocument.objects.create(
            title='گمشده', file='documents/gone.pdf',
            degree_level='bachelor_continuous', category='form', is_active=True)
        self.assertIn('File Manager', self._run())

    def test_an_empty_field_is_not_reported_as_missing(self):
        from core.models import DownloadableDocument

        DownloadableDocument.objects.create(
            title='بدون فایل', degree_level='bachelor_continuous',
            category='form', is_active=True, external_url='https://x.test/')
        self.assertIn('روی سرور هستند', self._run())
