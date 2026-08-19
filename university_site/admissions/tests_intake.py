"""تست‌های سه بهبود مسیر پذیرش.

پیش‌نویس فرم، خط زمانی وضعیت، و بررسی کیفیت مدارک.
"""
import io

from django.test import TestCase, override_settings
from django.urls import reverse

from academics.models import Department, Major
from admissions.models import Application, ApplicationDraft


def make_application(**kwargs):
    department = Department.objects.create(name='فنی')
    major = Major.objects.create(
        name='کامپیوتر', degree='bachelor_cont',
        department=department, is_active=True,
    )
    values = {
        'first_name': 'علی', 'last_name': 'رضایی',
        'national_id': '1234567891', 'phone': '09120000000',
        'address': 'بابلسر', 'degree': 'bachelor_cont',
        'desired_major': major, 'status': 'pending',
    }
    values.update(kwargs)
    return Application.objects.create(**values)


@override_settings(SMS_ENABLED=False)
class DraftTests(TestCase):
    """فرم چهل فیلد دارد؛ نصفه‌ماندنش نباید یعنی از صفر."""

    def test_only_non_empty_strings_are_kept(self):
        ApplicationDraft.store('09120000000', {
            'first_name': 'علی', 'last_name': '  ', 'father_name': '',
        })
        payload = ApplicationDraft.load('09120000000')
        self.assertEqual(payload, {'first_name': 'علی'})

    def test_secrets_are_never_stored(self):
        ApplicationDraft.store('09120000000', {
            'first_name': 'علی',
            'csrfmiddlewaretoken': 'abc',
            'captcha': '12',
            'password1': 'hunter2',
        })
        payload = ApplicationDraft.load('09120000000')
        self.assertEqual(list(payload), ['first_name'])

    def test_storing_twice_replaces_rather_than_duplicates(self):
        ApplicationDraft.store('09120000000', {'first_name': 'علی'})
        ApplicationDraft.store('09120000000', {'first_name': 'رضا'})
        self.assertEqual(ApplicationDraft.objects.count(), 1)
        self.assertEqual(
            ApplicationDraft.load('09120000000')['first_name'], 'رضا')

    def test_clear_removes_it(self):
        ApplicationDraft.store('09120000000', {'first_name': 'علی'})
        ApplicationDraft.clear('09120000000')
        self.assertEqual(ApplicationDraft.load('09120000000'), {})

    def test_load_of_an_unknown_phone_is_empty(self):
        self.assertEqual(ApplicationDraft.load('09999999999'), {})
        self.assertEqual(ApplicationDraft.load(''), {})

    def test_the_endpoint_needs_a_verified_session(self):
        response = self.client.post(reverse('admissions:save_draft'),
                                    {'first_name': 'علی'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['ok'])
        self.assertEqual(ApplicationDraft.objects.count(), 0)

    def test_the_endpoint_saves_for_a_verified_session(self):
        session = self.client.session
        session['apply_phone'] = '09120000000'
        session.save()
        response = self.client.post(reverse('admissions:save_draft'),
                                    {'first_name': 'علی'})
        self.assertTrue(response.json()['ok'])
        self.assertEqual(
            ApplicationDraft.load('09120000000'), {'first_name': 'علی'})

    def test_get_is_rejected(self):
        response = self.client.get(reverse('admissions:save_draft'))
        self.assertEqual(response.status_code, 405)

    def test_discard_wipes_the_draft(self):
        session = self.client.session
        session['apply_phone'] = '09120000000'
        session.save()
        ApplicationDraft.store('09120000000', {'first_name': 'علی'})
        self.client.post(reverse('admissions:discard_draft'))
        self.assertEqual(ApplicationDraft.objects.count(), 0)


@override_settings(SMS_ENABLED=False)
class TrackingTimelineTests(TestCase):
    """هر مرحله باید توضیح داشته باشد، و ناقص باید بگوید چه چیزی."""

    def test_every_step_carries_a_hint(self):
        from admissions import tracking
        for step in tracking.build(make_application()):
            self.assertTrue(step['hint'], step)

    def test_a_rejected_file_shows_no_future_steps(self):
        from admissions import tracking
        steps = tracking.build(make_application(status='rejected'))
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]['state'], 'current')

    def test_an_incomplete_file_lists_what_is_missing(self):
        from admissions import tracking
        steps = tracking.build(make_application(status='incomplete'))
        current = [s for s in steps if s['state'] == 'current'][0]
        self.assertIn('تصویر کارت ملی', current['missing'])
        self.assertIn('عکس پرسنلی', current['missing'])

    def test_a_filled_field_is_not_reported_missing(self):
        from admissions import tracking
        app = make_application(status='incomplete', prev_major='ریاضی')
        gaps = tracking.missing_items(app)
        self.assertNotIn('رشتهٔ مدرک قبلی', gaps)
        self.assertNotIn('کد ملی', gaps)

    def test_the_accepted_flow_marks_earlier_steps_done(self):
        from admissions import tracking
        steps = tracking.build(make_application(status='accepted'))
        self.assertEqual(steps[-1]['state'], 'current')
        self.assertTrue(all(s['state'] == 'done' for s in steps[:-1]))


class DocumentQualityTests(TestCase):
    """تصویر ریز، بزرگ که شود ناخواناست و باید همان اول رد شود."""

    def _image(self, width, height):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buffer = io.BytesIO()
        Image.new('RGB', (width, height), (200, 200, 200)).save(buffer, 'PNG')
        return SimpleUploadedFile('doc.png', buffer.getvalue(),
                                  content_type='image/png')

    def test_a_tiny_image_is_rejected(self):
        from core.iran import validate_image_upload
        error = validate_image_upload(self._image(120, 90), 'کارت ملی')
        self.assertIsNotNone(error)
        self.assertIn('کم‌کیفیت', error)

    def test_a_large_enough_image_passes(self):
        from core.iran import validate_image_upload
        self.assertIsNone(
            validate_image_upload(self._image(800, 600), 'کارت ملی'))

    def test_the_file_stays_readable_after_the_check(self):
        """بررسی ابعاد نباید نشانگر فایل را جابه‌جا رها کند.

        اگر رها شود، ذخیرهٔ بعدی یک فایل صفر بایتی می‌نویسد و هیچ
        خطایی هم نمی‌دهد — بدترین حالت.
        """
        from core.iran import validate_image_upload
        upload = self._image(800, 600)
        validate_image_upload(upload, 'کارت ملی')
        upload.seek(0)
        self.assertTrue(upload.read())

    def test_a_non_image_is_still_caught_first(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.iran import validate_image_upload
        bad = SimpleUploadedFile('x.txt', b'hello', content_type='text/plain')
        error = validate_image_upload(bad, 'کارت ملی')
        self.assertIn('تصویر', error)

    def test_an_absent_optional_file_is_fine(self):
        from core.iran import validate_image_upload
        self.assertIsNone(validate_image_upload(None, 'کارت ملی'))
