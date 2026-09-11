"""فایل رسیدِ پرداخت آفلاین، پیش از نشستن روی دیسک بررسی شود.

ثبت پرداخت آفلاین هیچ بررسی‌ای روی فایل نداشت: نه نوع، نه حجم. یعنی
هر فایلی با هر اندازه‌ای در \u200Emedia\u200E می‌نشست — جایی که وب‌سرور مستقیم
سروش می‌کند و جنگو در مسیرش نیست.
"""
import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from dashboard.models import Payment, Semester


def _image(width=900, height=1200):
    from PIL import Image

    buffer = io.BytesIO()
    Image.new('RGB', (width, height), '#ffffff').save(buffer, format='JPEG')
    return SimpleUploadedFile(
        'receipt.jpg', buffer.getvalue(), content_type='image/jpeg')


@override_settings(MEDIA_ROOT='/tmp/test-tuition-receipts')
class TheOfflineReceiptIsCheckedTests(TestCase):

    def setUp(self):
        from accounts.models import UserProfile

        self.user = User.objects.create_user('9912345', password='x')
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'role': 'student'})
        UserProfile.objects.filter(user=self.user).update(role='student')
        self.client.force_login(self.user)

        from datetime import date

        self.semester = Semester.objects.create(
            name='نیم‌سال آزمایشی', academic_year='۱۴۰۵-۱۴۰۶',
            semester_type='fall', is_active=True,
            start_date=date(2026, 9, 22), end_date=date(2027, 1, 20))
        self.payment = Payment.objects.create(
            student=self.user, payment_type='tuition', amount=1000000,
            semester=self.semester, status='pending',
            installment_no=1, installment_stage='initial')
        self.url = reverse('dashboard:payment_offline',
                           args=[self.payment.pk])

    def _post(self, upload):
        return self.client.post(self.url, {
            'method': 'bank_deposit',
            'receipt_ref': '123456',
            'receipt_file': upload,
        }, follow=True)

    def _status(self):
        self.payment.refresh_from_db()
        return self.payment.status

    def test_a_real_receipt_is_accepted(self):
        self._post(_image())
        self.assertEqual(self._status(), 'review')

    def test_a_pdf_receipt_is_accepted(self):
        """خروجی اپ بانک معمولاً PDF است، نه عکس."""
        pdf = SimpleUploadedFile(
            'receipt.pdf', b'%PDF-1.4 receipt',
            content_type='application/pdf')
        self._post(pdf)
        self.assertEqual(self._status(), 'review')

    def test_an_executable_is_refused(self):
        bad = SimpleUploadedFile(
            'receipt.php', b'<?php echo 1; ?>', content_type='text/plain')
        response = self._post(bad)
        self.assertEqual(self._status(), 'pending')
        self.assertContains(response, 'PDF')

    def test_a_page_that_could_run_in_the_browser_is_refused(self):
        """media را وب‌سرور از همان دامنه سرو می‌کند."""
        bad = SimpleUploadedFile(
            'receipt.html', b'<script>alert(1)</script>',
            content_type='text/html')
        self._post(bad)
        self.assertEqual(self._status(), 'pending')

    def test_an_oversized_file_is_refused(self):
        big = SimpleUploadedFile(
            'receipt.jpg', b'x' * (6 * 1024 * 1024),
            content_type='image/jpeg')
        response = self._post(big)
        self.assertEqual(self._status(), 'pending')
        self.assertContains(response, 'مگابایت')

    def test_a_reference_number_alone_still_works(self):
        """رسید اختیاری است؛ شماره پیگیری کافی است."""
        self.client.post(self.url, {
            'method': 'bank_deposit', 'receipt_ref': '123456'}, follow=True)
        self.assertEqual(self._status(), 'review')

    def test_a_refused_file_leaves_nothing_behind(self):
        bad = SimpleUploadedFile(
            'receipt.php', b'<?php echo 1; ?>', content_type='text/plain')
        self._post(bad)
        self.payment.refresh_from_db()
        self.assertFalse(self.payment.receipt_file)
