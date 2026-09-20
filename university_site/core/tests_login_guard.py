"""در ورود، پس از چند تلاش ناموفق بسته شود.

کپچا جلوی ربات ساده را می‌گرفت، ولی نه سرویس‌های حل‌کپچا را، نه
حمله‌ای که یک رمزِ پرتکرار را روی هزار کد ملی امتحان می‌کند، و نه
\u200E/admin/login/\u200E را که اصلاً کپچا ندارد.
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings

from core import login_guard


@override_settings(CAPTCHA_ENABLED=False)
class TheDoorClosesAfterTooManyTriesTests(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            'daneshjoo', 'd@aab.ac.ir', 'Str0ng!Pass2026')

    def _try(self, password='غلط', **extra):
        return self.client.post('/accounts/login/', {
            'national_id': 'daneshjoo', 'password': password}, **extra)

    def test_a_few_mistakes_are_forgiven(self):
        """کاربر واقعی هم رمزش را اشتباه می‌زند."""
        for _ in range(3):
            self.assertEqual(self._try().status_code, 200)

    def test_the_door_shuts_after_the_limit(self):
        for _ in range(login_guard.MAX_FAILURES):
            self._try()
        self.assertEqual(self._try().status_code, 429)

    def test_the_right_password_is_not_even_checked_once_locked(self):
        """وگرنه قفل فقط تأخیر بود، نه مانع."""
        for _ in range(login_guard.MAX_FAILURES):
            self._try()
        response = self._try(password='Str0ng!Pass2026')
        self.assertEqual(response.status_code, 429)
        self.assertFalse(
            response.wsgi_request.user.is_authenticated)

    def test_it_says_when_to_come_back(self):
        for _ in range(login_guard.MAX_FAILURES):
            self._try()
        self.assertEqual(self._try()['Retry-After'],
                         str(login_guard.LOCK_SECONDS))

    def test_a_successful_login_wipes_the_slate(self):
        """وگرنه کاربری که بالاخره یادش آمد، بعداً قفل می‌شد."""
        for _ in range(login_guard.MAX_FAILURES - 1):
            self._try()
        self.client.post('/accounts/login/', {
            'national_id': 'daneshjoo', 'password': 'Str0ng!Pass2026'})
        self.client.logout()
        self.assertEqual(self._try().status_code, 200)

    def test_changing_the_source_address_does_not_open_it(self):
        """حملهٔ توزیع‌شده روی یک حساب هم باید بسته شود."""
        for index in range(login_guard.MAX_FAILURES):
            self._try(HTTP_X_FORWARDED_FOR='10.0.0.%d' % index)
        self.assertEqual(
            self._try(HTTP_X_FORWARDED_FOR='10.0.0.250').status_code, 429)

    def test_another_account_from_a_fresh_address_still_works(self):
        """قفل نباید کلِ سایت را ببندد."""
        for index in range(login_guard.MAX_FAILURES):
            self._try(HTTP_X_FORWARDED_FOR='10.0.0.%d' % index)
        response = self.client.post(
            '/accounts/login/',
            {'national_id': 'digari', 'password': 'x'},
            HTTP_X_FORWARDED_FOR='10.0.0.251')
        self.assertEqual(response.status_code, 200)

    def test_the_admin_login_is_guarded_too(self):
        """صفحه‌ای که کپچا ندارد، بیشتر هم نیاز دارد."""
        for _ in range(login_guard.MAX_FAILURES):
            self.client.post('/admin/login/',
                             {'username': 'modir', 'password': 'غلط'})
        response = self.client.post('/admin/login/',
                                    {'username': 'modir', 'password': 'غلط'})
        self.assertEqual(response.status_code, 429)

    def test_browsing_the_site_is_never_throttled(self):
        for _ in range(login_guard.MAX_FAILURES + 4):
            self._try()
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_the_proxy_address_is_not_taken_for_everyone(self):
        """پشت LiteSpeed همهٔ کاربران یک REMOTE_ADDR می‌گیرند."""
        request = self.client.request().wsgi_request
        request.META['HTTP_X_FORWARDED_FOR'] = '5.6.7.8, 10.0.0.1'
        self.assertEqual(login_guard._client_ip(request), '5.6.7.8')
