from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.urls import reverse


class PasswordRecoveryIsReachableTests(TestCase):
    """راه بازیابی باید از هر دو صفحهٔ ورود و ثبت‌نام دیده شود.

    سه خطای فرم ثبت‌نام («این کد ملی قبلاً ثبت‌نام شده است») دقیقاً
    یعنی کاربر حساب دارد و رمزش را فراموش کرده. تا امروز آن صفحه
    فقط به «ورود» لینک می‌داد، یعنی یک کلیک اضافه در بدترین لحظه.
    """

    def test_login_page_links_to_recovery(self):
        html = self.client.get(reverse('accounts:login')).content.decode()
        self.assertIn(reverse('accounts:password_reset_request'), html)

    def test_register_page_links_to_recovery(self):
        html = self.client.get(reverse('accounts:register')).content.decode()
        self.assertIn(reverse('accounts:password_reset_request'), html)
