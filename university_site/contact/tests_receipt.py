"""ارسال فیش واریزی شهریه از فرم تماس با ما.

دانشجو شهریه را در بانک واریز می‌کند و تا امروز راهی نبود که رسیدش
را به موسسه برساند جز مراجعهٔ حضوری یا واتساپِ کارمند. حالا از همان
فرم تماس می‌فرستد و در پنل، کنارِ شمارهٔ دانشجویی‌اش می‌نشیند.
"""
import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from contact.models import ContactMessage


def _image(width=900, height=1200, fmt='JPEG'):
    """یک عکس واقعی می‌سازد؛ ImageField فایل قلابی را نمی‌پذیرد."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new('RGB', (width, height), '#ffffff').save(buffer, format=fmt)
    return SimpleUploadedFile(
        'receipt.jpg', buffer.getvalue(), content_type='image/jpeg')


class TheFormOffersTheReceiptTests(TestCase):
    """گزینه باید در خودِ فرم دیده شود، نه فقط در مدل."""

    def setUp(self):
        self.url = reverse('contact:contact')

    def test_the_subject_is_listed(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('ارسال فیش واریزی شهریه', html)

    def test_the_form_can_carry_a_file(self):
        """بدون enctype مرورگر فقط نامِ فایل را می‌فرستد، نه خودش."""
        html = self.client.get(self.url).content.decode()
        self.assertIn('enctype="multipart/form-data"', html)

    def test_both_receipt_fields_are_on_the_page(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('name="attachment"', html)
        self.assertIn('name="student_number"', html)

    def test_they_start_hidden(self):
        """تا موضوعِ فیش انتخاب نشده، دو فیلد اضافه دیده نمی‌شوند."""
        html = self.client.get(self.url).content.decode()
        box = html.split('id="receiptFileBox"')[1].split('>')[0]
        self.assertIn('hidden', box)

    def test_it_opens_straight_onto_the_receipt_form(self):
        """لینک مستقیم، تا بشود از صفحهٔ شهریه به اینجا آورد."""
        response = self.client.get(self.url + '?to=tuition_receipt')
        html = response.content.decode()
        self.assertIn('ارسال فیش واریزی شهریه', html)
        chunk = html.split('value="tuition_receipt"')[1].split('>')[0]
        self.assertIn('selected', chunk)


@override_settings(MEDIA_ROOT='/tmp/test-receipts')
class SendingAReceiptTests(TestCase):

    def setUp(self):
        self.url = reverse('contact:contact')

    def _post(self, follow=False, **extra):
        data = {
            'full_name': 'نمونهٔ دانشجو',
            'email': 'student@example.org',
            'subject': 'tuition_receipt',
            'message': 'شهریه نیم‌سال اول واریز شد.',
            'student_number': '۹۹۱۲۳۴۵۶',
        }
        data.update(extra)
        return self.client.post(self.url, data, follow=follow)

    def test_a_complete_receipt_is_stored(self):
        self._post(attachment=_image())
        row = ContactMessage.objects.get()
        self.assertEqual(row.subject, 'tuition_receipt')
        self.assertTrue(row.attachment)

    def test_the_student_number_is_stored_in_latin_digits(self):
        """دانشجو با صفحه‌کلید فارسی تایپ می‌کند؛ جست‌وجوی امور مالی
        با ارقام لاتین است."""
        self._post(attachment=_image())
        self.assertEqual(ContactMessage.objects.get().student_number,
                         '99123456')

    def test_a_receipt_without_an_image_is_refused(self):
        response = self._post()
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, 'الزامی')

    def test_a_receipt_without_a_student_number_is_refused(self):
        """عکسِ واریزی که معلوم نیست به حساب چه کسی بنشیند، بی‌مصرف است."""
        response = self._post(student_number='', attachment=_image())
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, 'شمارهٔ دانشجویی')

    def test_what_was_typed_survives_a_refusal(self):
        """اگر متن پاک شود، دانشجو بار دوم حوصله نمی‌کند."""
        response = self._post()
        self.assertContains(response, 'نمونهٔ دانشجو')
        self.assertContains(response, 'شهریه نیم‌سال اول واریز شد.')

    def test_a_file_that_is_not_an_image_is_refused(self):
        bad = SimpleUploadedFile(
            'receipt.pdf', b'%PDF-1.4 nope', content_type='application/pdf')
        response = self._post(attachment=bad)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, 'تصویر')

    def test_an_oversized_image_is_refused(self):
        big = SimpleUploadedFile(
            'receipt.jpg', b'x' * (6 * 1024 * 1024), content_type='image/jpeg')
        response = self._post(attachment=big)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, 'مگابایت')

    def test_an_unreadably_small_image_is_refused(self):
        """فیشی که بزرگ هم بشود خوانا نیست، کارمند را پای تلفن می‌برد."""
        response = self._post(attachment=_image(120, 90))
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_a_phone_photo_is_shrunk_on_the_way_in(self):
        """صدها فیشِ چهار مگابایتی دیسک سرور را می‌خورد."""
        self._post(attachment=_image(4000, 3000))
        row = ContactMessage.objects.get()
        self.assertLessEqual(row.attachment.width, 1600)

    def test_the_student_is_told_where_the_receipt_went(self):
        response = self._post(attachment=_image(), follow=True)
        self.assertContains(response, 'امور مالی')


class OrdinaryMessagesStillWorkTests(TestCase):
    """فیش نباید بقیهٔ فرم را سخت‌گیرتر کرده باشد."""

    def setUp(self):
        self.url = reverse('contact:contact')

    def test_a_plain_message_needs_no_file(self):
        self.client.post(self.url, {
            'full_name': 'نمونه',
            'email': 'a@example.org',
            'subject': 'general',
            'message': 'سلام',
        })
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_a_plain_message_needs_no_student_number(self):
        self.client.post(self.url, {
            'full_name': 'نمونه',
            'email': 'a@example.org',
            'subject': 'academic',
            'message': 'سلام',
        })
        self.assertEqual(ContactMessage.objects.get().student_number, '')

    def test_an_unknown_subject_falls_back_instead_of_crashing(self):
        self.client.post(self.url, {
            'full_name': 'نمونه',
            'email': 'a@example.org',
            'subject': 'چنین-چیزی-نیست',
            'message': 'سلام',
        })
        self.assertEqual(ContactMessage.objects.get().subject, 'general')


@override_settings(MEDIA_ROOT='/tmp/test-receipts')
class TheFinanceOfficeCanUseThemTests(TestCase):
    """فیش در پنل باید پیدا و خوانده شود، وگرنه فرستادنش بی‌فایده است."""

    def setUp(self):
        self.client.force_login(User.objects.create_superuser(
            'boss', 'boss@example.org', 'x'))
        self.row = ContactMessage.objects.create(
            full_name='نمونهٔ دانشجو', email='s@example.org',
            subject='tuition_receipt', message='واریز شد',
            student_number='99123456',
            attachment=_image())

    def test_the_list_shows_which_messages_carry_a_receipt(self):
        html = self.client.get(
            reverse('admin:contact_contactmessage_changelist')).content.decode()
        self.assertIn('فیش', html)

    def test_it_is_searchable_by_student_number(self):
        url = reverse('admin:contact_contactmessage_changelist')
        html = self.client.get(url, {'q': '99123456'}).content.decode()
        self.assertIn('نمونهٔ دانشجو', html)

    def test_the_image_is_shown_and_links_to_full_size(self):
        html = self.client.get(reverse(
            'admin:contact_contactmessage_change',
            args=[self.row.pk])).content.decode()
        self.assertIn('<img src="%s"' % self.row.attachment.url, html)
        self.assertIn('href="%s"' % self.row.attachment.url, html)

    def test_a_message_without_a_receipt_does_not_break_the_page(self):
        plain = ContactMessage.objects.create(
            full_name='نمونه', email='a@example.org', message='سلام')
        response = self.client.get(reverse(
            'admin:contact_contactmessage_change', args=[plain.pk]))
        self.assertEqual(response.status_code, 200)
