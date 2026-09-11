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


class RegistrationIsNoLongerLockedBehindTuitionTests(TestCase):
    """قفل «قسط اول پرداخت نشده ← انتخاب واحد بسته» به درخواست موسسه رفت.

    پیش از این دانشجویی که هنوز پرداخت نکرده بود، با بازکردن صفحهٔ
    انتخاب واحد به صفحهٔ پرداخت پرتاب می‌شد — بی‌آنکه حتی ببیند چه
    درس‌هایی ارائه شده.
    """

    def setUp(self):
        from datetime import date

        from accounts.models import UserProfile
        from academics.models import Department, Major

        self.user = User.objects.create_user('9954321', password='x')
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'role': 'student'})
        dept = Department.objects.create(name='دانشکدهٔ نمونه', slug='d1')
        self.major = Major.objects.create(
            name='رشتهٔ نمونه', slug='m1', department=dept, degree='bachelor')
        UserProfile.objects.filter(user=self.user).update(
            role='student', major=self.major)
        self.client.force_login(self.user)

        self.semester = Semester.objects.create(
            name='نیم‌سال آزمایشی', academic_year='۱۴۰۵-۱۴۰۶',
            semester_type='fall', is_active=True, registration_open=True,
            start_date=date(2026, 9, 22), end_date=date(2027, 1, 20))

    def test_the_page_opens_without_paying(self):
        response = self.client.get(reverse('dashboard:student_registration'))
        self.assertEqual(response.status_code, 200)

    def test_it_does_not_bounce_to_payments(self):
        response = self.client.get(reverse('dashboard:student_registration'))
        self.assertNotIn('Location', response)

    def test_the_student_is_reminded_not_blocked(self):
        """یادآوری می‌ماند؛ فقط دیگر در بسته نیست."""
        response = self.client.get(
            reverse('dashboard:student_registration'), follow=True)
        self.assertContains(response, 'قسط اول')

    def test_the_journey_points_at_registration_not_payment(self):
        """نشانگرِ «مرحلهٔ بعدی» هم دیگر به صفحهٔ پرداخت نمی‌بَرد.

        مسیر دانشجو از پروندهٔ پذیرش شروع می‌شود، پس بدون آن اصلاً به
        این شاخه نمی‌رسد و به صفحهٔ پیگیری می‌رود.
        """
        from admissions.models import Application
        from dashboard.onboarding import next_journey_url

        Application.objects.create(
            national_id='9954321', status='accepted',
            desired_major=self.major,
            first_name='نمونه', last_name='دانشجو')

        self.assertEqual(next_journey_url(user=self.user),
                         reverse('dashboard:student_registration'))

    def test_the_registration_step_is_not_marked_locked(self):
        from dashboard.onboarding import build_journey_status

        steps = {s['key']: s for s in
                 build_journey_status(user=self.user)['steps']}
        self.assertFalse(steps['registration']['locked'])

    def test_the_exam_card_is_still_locked_until_fully_settled(self):
        """این قفل سرِ جایش می‌ماند — موسسه فقط انتخاب واحد را خواست."""
        from dashboard.onboarding import build_journey_status

        steps = {s['key']: s for s in
                 build_journey_status(user=self.user)['steps']}
        self.assertTrue(steps['exam_card']['locked'])
