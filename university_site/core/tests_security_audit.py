"""حفره‌هایی که در بازبینی امنیتی پیدا و بسته شدند — تا دوباره باز نشوند."""
import tempfile
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings

from contact.models import ContactMessage
from core import private_media
from core.iran import validate_document_upload
from dashboard.forms import AssignmentSubmissionForm


class AStudentUploadNeverRunsInTheStaffBrowserTests(TestCase):
    """پیوست html/svg از همین دامنه inline باز می‌شد: XSS با نشست کارمند."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        folder = Path(self.tmp.name) / 'requests'
        folder.mkdir()
        (folder / 'evil.html').write_text('<script>alert(1)</script>')
        (folder / 'ok.pdf').write_bytes(b'%PDF-1.4')
        self.staff = User.objects.create_user('kar', password='x', is_staff=True)

    def _get(self, name):
        with override_settings(MEDIA_ROOT=self.tmp.name):
            request = RequestFactory().get('/media/requests/' + name)
            request.user = self.staff
            return private_media.serve(request, 'requests/' + name)

    def test_html_is_downloaded_not_rendered(self):
        response = self._get('evil.html')
        self.assertTrue(response['Content-Disposition'].startswith('attachment'))
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        response.close()

    def test_a_pdf_still_opens_in_the_browser(self):
        response = self._get('ok.pdf')
        self.assertTrue(response['Content-Disposition'].startswith('inline'))
        response.close()

    def test_scriptable_types_are_refused_at_upload(self):
        for name in ('a.html', 'a.svg', 'a.js', 'a.htm', 'noext'):
            f = SimpleUploadedFile(name, b'x', content_type='text/plain')
            self.assertIsNotNone(validate_document_upload(f), name)
        f = SimpleUploadedFile('a.pdf', b'%PDF', content_type='application/pdf')
        self.assertIsNone(validate_document_upload(f))

    def test_the_submission_form_rejects_html(self):
        form = AssignmentSubmissionForm(
            data={}, files={'file': SimpleUploadedFile(
                'x.html', b'<script>', content_type='text/html')})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)


class ATooLongValueIsClippedNotA500Tests(TestCase):
    """MySQL strict: متن بلندتر از ستون یعنی DataError و صفحهٔ خطای سرور."""

    def test_phone_longer_than_the_column_is_clipped(self):
        msg = ContactMessage.objects.create(phone='0912 345 6789 (منزل)')
        msg.refresh_from_db()
        self.assertEqual(len(msg.phone), ContactMessage._meta.get_field('phone').max_length)


class TheAdmissionFormDoesNotLeakTrackingCodesTests(TestCase):
    """کد ملی محرمانه نیست؛ کد رهگیری به‌تنهایی پرونده را باز می‌کند."""

    @override_settings(ADMISSION_REQUIRE_MOBILE_OTP=False)
    def test_a_duplicate_national_id_does_not_reveal_the_code(self):
        from academics.models import Department, Major
        from admissions.models import Application
        major = Major.objects.create(
            name='کامپیوتر', degree='bachelor_cont', is_active=True,
            department=Department.objects.create(name='فنی'))
        app = Application.objects.create(
            first_name='الف', last_name='ب', national_id='0013542419',
            phone='09120000000', degree='bachelor_cont', address='x',
            desired_major=major)
        response = self.client.post('/پذیرش/ثبت-درخواست/', {
            'national_id': '0013542419'}, follow=True)
        self.assertNotContains(response, app.tracking_code)


class APaymentCannotBorrowAnotherPaymentsAuthorityTests(TestCase):
    """زرین‌پال برای تراکنشِ قبلاً تأییدشده ۱۰۱ می‌دهد؛ authority باید مال همین ردیف باشد."""

    def test_mismatched_authority_is_refused_before_the_gateway_is_asked(self):
        from dashboard.models import Payment
        from dashboard import payment_gateway
        student = User.objects.create_user('d', password='x')
        paid = Payment.objects.create(student=student, payment_type='tuition',
                                      amount=1000, status='paid',
                                      authority='A-PAID', gateway='zarinpal')
        other = Payment.objects.create(student=student, payment_type='tuition',
                                       amount=1000, status='pending',
                                       authority='A-OTHER', gateway='zarinpal')
        request = RequestFactory().get('/', {'Authority': paid.authority})
        with mock.patch.object(payment_gateway, '_zarinpal_verify',
                               return_value=True) as verify:
            ok = payment_gateway.verify_payment(request, other, authority=paid.authority)
        self.assertFalse(ok)
        verify.assert_not_called()
        other.refresh_from_db()
        self.assertEqual(other.status, 'pending')
