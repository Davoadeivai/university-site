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

    def test_a_receipt_without_an_image_is_still_accepted(self):
        """موسسه خواست هیچ فیلدی اجباری نباشد.

        بهایش این است که پیامی با موضوع فیش ولی بدون تصویر هم ثبت
        می‌شود؛ ستون «فیش» در پنل خالی می‌ماند و کارمند می‌بیند که
        چیزی پیوست نشده.
        """
        self._post()
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertFalse(ContactMessage.objects.get().attachment)

    def test_a_receipt_without_a_student_number_is_still_accepted(self):
        self._post(student_number='', attachment=_image())
        self.assertEqual(ContactMessage.objects.get().student_number, '')

    def test_what_was_typed_survives_a_refusal(self):
        """اگر متن پاک شود، دانشجو بار دوم حوصله نمی‌کند."""
        bad = SimpleUploadedFile(
            'receipt.pdf', b'%PDF-1.4 nope', content_type='application/pdf')
        response = self._post(attachment=bad)
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


class TheWayInIsVisibleEverywhereTests(TestCase):
    """گزینه در کشوی موضوع هست، ولی کسی کشو را باز نمی‌کند تا ببیند.

    دانشجویی که شهریه را واریز کرده، سه جا ممکن است باشد: صفحهٔ
    شهریه، صفحهٔ تماس، یا صفحهٔ اصلی. از هر سه باید راهی ببیند.
    """

    def _link(self):
        return reverse('contact:contact') + '?to=tuition_receipt'

    def test_the_tuition_page_points_at_it(self):
        html = self.client.get(
            reverse('admissions:tuition')).content.decode()
        self.assertIn('ارسال فیش واریزی', html)
        self.assertIn('to=tuition_receipt', html)

    def test_the_contact_page_has_a_shortcut_above_the_form(self):
        """فرم همان‌جاست؛ دکمه موضوع را انتخاب می‌کند، نه اینکه لینک
        به خودِ صفحه بدهد."""
        html = self.client.get(reverse('contact:contact')).content.decode()
        self.assertIn('id="pickReceipt"', html)
        self.assertLess(html.index('pickReceipt'), html.index('id="contactForm"'))

    def test_the_home_quick_links_carry_it(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_receipt_link', stdout=StringIO())
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('ارسال فیش واریزی', html)


class TheQuickLinkTileTests(TestCase):
    """کاشیِ دسترسی سریع، و آنچه نباید به آن دست بزند."""

    def _run(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_receipt_link', stdout=StringIO())

    def test_it_creates_the_tile(self):
        from core.models import QuickLink

        self._run()
        row = QuickLink.objects.get(category='home')
        self.assertEqual(row.title, 'ارسال فیش واریزی')
        self.assertIn('to=tuition_receipt', row.url)

    def test_running_it_twice_makes_one_tile(self):
        from core.models import QuickLink

        self._run()
        self._run()
        self.assertEqual(QuickLink.objects.filter(category='home').count(), 1)

    def test_a_title_edited_in_the_panel_survives_a_deploy(self):
        """اگر هر بار بازنویسی می‌شد، ویرایش موسسه بی‌صدا از بین می‌رفت."""
        from core.models import QuickLink

        self._run()
        QuickLink.objects.filter(category='home').update(
            title='فرستادن رسید بانکی', order=2)

        self._run()
        row = QuickLink.objects.get(category='home')
        self.assertEqual(row.title, 'فرستادن رسید بانکی')
        self.assertEqual(row.order, 2)

    def test_a_stale_address_is_corrected(self):
        """نشانی مالِ کد است؛ اگر مسیر فرم عوض شود کاشی نباید ۴۰۴ بدهد."""
        from core.models import QuickLink

        self._run()
        QuickLink.objects.filter(category='home').update(
            url='/غلط/?to=tuition_receipt')

        self._run()
        self.assertIn('to=tuition_receipt',
                      QuickLink.objects.get(category='home').url)

    def test_it_does_not_wipe_links_added_in_the_panel(self):
        """sync_official_eservices این کار را می‌کند؛ این یکی نباید."""
        from core.models import QuickLink

        QuickLink.objects.create(
            title='لینک دستی موسسه', url='https://example.org',
            category='home', order=3, is_active=True)
        self._run()
        self.assertTrue(
            QuickLink.objects.filter(title='لینک دستی موسسه').exists())

    def test_it_runs_on_every_deploy(self):
        from core.tests_deploy import _content_commands

        self.assertIn('seed_receipt_link', _content_commands())


class TheHomeGridHasRoomForItTests(TestCase):
    """هشت کاشی ثبت شده بود و سقف هم هشت — کاشی نهم یکی را می‌انداخت."""

    def test_a_ninth_tile_does_not_push_one_out(self):
        from core.models import QuickLink

        for index in range(1, 10):
            QuickLink.objects.create(
                title='کاشی %d' % index, url='/%d/' % index,
                category='home', order=index, is_active=True)

        html = self.client.get(reverse('core:home')).content.decode()
        for index in range(1, 10):
            self.assertIn('کاشی %d' % index, html)


class NothingIsMandatoryTests(TestCase):
    """موسسه خواست ستاره‌ها برداشته شوند و همه‌چیز اختیاری باشد."""

    def setUp(self):
        self.url = reverse('contact:contact')

    def test_no_field_is_marked_required(self):
        html = self.client.get(self.url).content.decode()
        form = html.split('id="contactForm"')[1].split('</form>')[0]
        self.assertNotIn(' required', form)

    def test_no_label_carries_a_star(self):
        html = self.client.get(self.url).content.decode()
        form = html.split('id="contactForm"')[1].split('</form>')[0]
        for label in ('نام و نام خانوادگی', 'آدرس ایمیل', 'متن پیام',
                      'شماره دانشجویی', 'تصویر فیش واریزی'):
            chunk = form.split(label)[1].split('<')[0]
            self.assertNotIn('*', chunk, label)

    def test_the_javascript_no_longer_adds_it_back(self):
        """پیش از این، انتخاب موضوعِ فیش دو فیلد را اجباری می‌کرد."""
        html = self.client.get(self.url).content.decode()
        self.assertNotIn("setAttribute('required'", html)

    def test_a_message_with_only_a_name_is_accepted(self):
        self.client.post(self.url, {'full_name': 'نمونه'})
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_a_message_with_only_text_is_accepted(self):
        self.client.post(self.url, {'message': 'سلام'})
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_a_message_with_no_email_is_accepted(self):
        self.client.post(self.url, {'full_name': 'نمونه', 'message': 'سلام'})
        self.assertEqual(ContactMessage.objects.get().email, '')

    def test_a_completely_empty_form_is_not_stored(self):
        """این فیلدِ اجباری نیست، شرطِ «چیزی بنویس» است.

        بدون آن، یک کلیک روی دکمهٔ ارسال یک ردیف بی‌محتوا می‌سازد و
        صندوق پیام‌ها پر از ردیف‌هایی می‌شود که کارمند باید یکی‌یکی
        بازشان کند تا ببیند خالی‌اند.
        """
        response = self.client.post(self.url, {'subject': 'general'})
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, 'دست‌کم')


class TheNationalIdFieldTests(TestCase):
    """کد ملی، برای اینکه کارمند بتواند پیام را به پرونده وصل کند."""

    def setUp(self):
        self.url = reverse('contact:contact')

    def test_it_is_on_the_form(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('name="national_id"', html)
        self.assertIn('کد ملی', html)

    def test_it_is_stored(self):
        self.client.post(self.url, {
            'full_name': 'نمونه', 'message': 'سلام',
            'national_id': '2050123456'})
        self.assertEqual(ContactMessage.objects.get().national_id, '2050123456')

    def test_persian_digits_are_normalised(self):
        """کارمند با ارقام لاتین جست‌وجو می‌کند."""
        self.client.post(self.url, {
            'full_name': 'نمونه', 'national_id': '۲۰۵۰۱۲۳۴۵۶'})
        self.assertEqual(ContactMessage.objects.get().national_id, '2050123456')

    def test_it_is_optional(self):
        self.client.post(self.url, {'full_name': 'نمونه'})
        self.assertEqual(ContactMessage.objects.get().national_id, '')

    def test_the_panel_can_search_by_it(self):
        ContactMessage.objects.create(
            full_name='نمونهٔ دانشجو', national_id='2050123456')
        self.client.force_login(User.objects.create_superuser(
            'boss2', 'boss2@example.org', 'x'))
        html = self.client.get(
            reverse('admin:contact_contactmessage_changelist'),
            {'q': '2050123456'}).content.decode()
        self.assertIn('نمونهٔ دانشجو', html)
