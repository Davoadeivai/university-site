"""تست‌های مسیر پذیرش: امنیت پیگیری، کد اصالت، یکتایی کد ملی، حذف تکرار ثبت‌نام.

اجرا:  python manage.py test admissions
"""
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from academics.models import Department, Major
from accounts.models import UserProfile
from admissions.models import Application
from admissions.verification import (
    check_verification_code, find_by_code, make_verification_code,
)

# کد ملی با رقم کنترلی معتبر — is_valid_national_id آن را می‌پذیرد
VALID_NID = '1122334451'


def make_application(**kw):
    dep = Department.objects.create(name='فنی و مهندسی')
    major = Major.objects.create(
        name='مهندسی کامپیوتر', degree='bachelor_cont',
        department=dep, is_active=True,
    )
    defaults = dict(
        first_name='مریم', last_name='رضایی', father_name='حسن',
        national_id=VALID_NID, phone='09121234567', email='m@example.com',
        gender='female', province='مازندران', city='بابلسر',
        address='بابلسر، خیابان اصلی', quota='region2',
        prev_degree='diploma', status='accepted',
        desired_major=major, degree='bachelor_cont',
    )
    defaults.update(kw)
    return Application.objects.create(**defaults)


@override_settings(SMS_ENABLED=False)
class NationalIdUniquenessTests(TestCase):
    def test_second_active_application_is_rejected(self):
        app = make_application()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Application.objects.create(
                    first_name='x', last_name='y', national_id=VALID_NID,
                    address='a', status='pending',
                    desired_major=app.desired_major, degree='bachelor_cont',
                )

    def test_reapply_allowed_after_rejection(self):
        app = make_application(status='rejected')
        second = Application.objects.create(
            first_name='مریم', last_name='رضایی', national_id=VALID_NID,
            address='a', status='pending',
            desired_major=app.desired_major, degree='bachelor_cont',
        )
        self.assertIsNotNone(second.pk)


@override_settings(SMS_ENABLED=False)
class VerificationCodeTests(TestCase):
    def setUp(self):
        self.app = make_application()

    def test_code_shape_and_roundtrip(self):
        code = make_verification_code(self.app)
        self.assertEqual(len(code), 11)
        self.assertIn('-', code)
        self.assertTrue(check_verification_code(self.app, code))

    def test_wrong_code_rejected(self):
        self.assertFalse(check_verification_code(self.app, 'AAAAA-BBBBB'))

    def test_code_is_case_and_dash_insensitive(self):
        code = make_verification_code(self.app)
        self.assertTrue(check_verification_code(self.app, code.lower().replace('-', ' ')))

    def test_reverse_lookup(self):
        found = find_by_code(make_verification_code(self.app))
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, self.app.pk)

    def test_public_verify_page_hides_identity(self):
        code = make_verification_code(self.app)
        res = self.client.get(reverse('admissions:verify'), {'code': code})
        body = res.content.decode()
        self.assertEqual(res.status_code, 200)
        self.assertIn('معتبر است', body)
        self.assertNotIn(VALID_NID, body)
        self.assertNotIn('رضایی', body)


@override_settings(SMS_ENABLED=False)
class TrackAccessTests(TestCase):
    def setUp(self):
        self.app = make_application()

    def test_national_id_requires_otp(self):
        res = self.client.get(reverse('admissions:track'), {'q': VALID_NID})
        body = res.content.decode()
        self.assertIn('تأیید هویت', body)
        self.assertNotIn(self.app.phone, body)

    def test_tracking_code_grants_direct_access(self):
        res = self.client.get(reverse('admissions:track'), {'q': self.app.tracking_code})
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('تأیید هویت', res.content.decode())

    def test_letter_blocked_for_anonymous(self):
        res = self.client.get(
            reverse('admissions:admission_letter', args=[self.app.tracking_code])
        )
        self.assertIn(res.status_code, (302, 403))


# کپچا اینجا خاموش است چون موضوع این تست‌ها منطق ثبت‌نام است، نه
# انسان‌بودن فرستنده. خودِ کپچا در core/tests.py آزموده می‌شود.
@override_settings(SMS_ENABLED=False, CAPTCHA_ENABLED=False)
class RegistrationDeduplicationTests(TestCase):
    """ثبت‌نام باید هویت را از پروندهٔ پذیرش بخواند، نه از کاربر."""

    def setUp(self):
        self.app = make_application()

    def test_account_created_from_application_data_only(self):
        res = self.client.post(reverse('accounts:register'), {
            'national_id': VALID_NID,
            'password1': 'Str0ng!Pass2026',
            'password2': 'Str0ng!Pass2026',
        })
        self.assertIn(res.status_code, (302, 200))
        user = User.objects.filter(username=VALID_NID).first()
        self.assertIsNotNone(user, 'حساب ساخته نشد')
        self.assertEqual(user.first_name, 'مریم')
        self.assertEqual(user.last_name, 'رضایی')
        self.assertEqual(user.email, 'm@example.com')

        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.phone, '09121234567')
        self.assertEqual(profile.province, 'مازندران')
        self.assertEqual(profile.city, 'بابلسر')
        self.assertEqual(profile.quota, 'region2')
        # این دو نباید از ورودی کاربر بیایند
        self.assertEqual(profile.student_id, '')
        self.assertEqual(profile.department, 'فنی و مهندسی')

    def test_user_supplied_identity_is_ignored(self):
        self.client.post(reverse('accounts:register'), {
            'national_id': VALID_NID,
            'password1': 'Str0ng!Pass2026',
            'password2': 'Str0ng!Pass2026',
            # تلاش برای جعل هویت هنگام ثبت‌نام
            'first_name': 'نام جعلی',
            'last_name': 'جعلی',
            'email': 'attacker@example.com',
            'student_id': '999999',
            'department': 'دانشکده جعلی',
        })
        user = User.objects.get(username=VALID_NID)
        self.assertEqual(user.first_name, 'مریم')
        self.assertEqual(user.email, 'm@example.com')
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.student_id, '')
        self.assertEqual(profile.department, 'فنی و مهندسی')

    @override_settings(REQUIRE_ACCEPTED_APPLICATION_FOR_SIGNUP=True)
    def test_gate_blocks_signup_without_accepted_application(self):
        """وقتی گیت روشن است، بدون پذیرش نهایی حساب ساخته نمی‌شود."""
        self.app.status = 'pending'
        self.app.save(update_fields=['status'])
        self.client.post(reverse('accounts:register'), {
            'national_id': VALID_NID,
            'first_name': 'مریم', 'last_name': 'رضایی', 'phone': '09121234567',
            'password1': 'Str0ng!Pass2026',
            'password2': 'Str0ng!Pass2026',
        })
        self.assertFalse(User.objects.filter(username=VALID_NID).exists())

    @override_settings(REQUIRE_ACCEPTED_APPLICATION_FOR_SIGNUP=False)
    def test_open_signup_without_application(self):
        """گیت خاموش: هویت از خود فرم گرفته می‌شود و حساب ساخته می‌شود."""
        self.app.status = 'pending'
        self.app.save(update_fields=['status'])
        self.client.post(reverse('accounts:register'), {
            'national_id': VALID_NID,
            'first_name': 'مریم', 'last_name': 'رضایی',
            'phone': '09121234567', 'email': 'm@example.com',
            'password1': 'Str0ng!Pass2026',
            'password2': 'Str0ng!Pass2026',
        })
        user = User.objects.filter(username=VALID_NID).first()
        self.assertIsNotNone(user, 'ثبت‌نام باز کار نکرد')
        self.assertEqual(user.first_name, 'مریم')
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.phone, '09121234567')
        # بدون پرونده، این‌ها هنوز تعیین نشده‌اند و نباید جعل شوند
        self.assertEqual(profile.student_id, '')
        self.assertIsNone(profile.major)

    @override_settings(REQUIRE_ACCEPTED_APPLICATION_FOR_SIGNUP=False)
    def test_open_signup_still_validates_mobile(self):
        self.app.status = 'pending'
        self.app.save(update_fields=['status'])
        self.client.post(reverse('accounts:register'), {
            'national_id': VALID_NID,
            'first_name': 'مریم', 'last_name': 'رضایی', 'phone': '12345',
            'password1': 'Str0ng!Pass2026',
            'password2': 'Str0ng!Pass2026',
        })
        self.assertFalse(User.objects.filter(username=VALID_NID).exists())

    @override_settings(REQUIRE_ACCEPTED_APPLICATION_FOR_SIGNUP=False)
    def test_application_data_still_wins_when_accepted(self):
        """گیت باز شدن نباید مسیر جعل هویت را باز کند."""
        self.client.post(reverse('accounts:register'), {
            'national_id': VALID_NID,
            'first_name': 'نام جعلی', 'last_name': 'جعلی',
            'phone': '09990000000', 'email': 'attacker@example.com',
            'password1': 'Str0ng!Pass2026',
            'password2': 'Str0ng!Pass2026',
        })
        user = User.objects.get(username=VALID_NID)
        self.assertEqual(user.first_name, 'مریم')
        self.assertEqual(user.email, 'm@example.com')
        self.assertEqual(UserProfile.objects.get(user=user).phone, '09121234567')
