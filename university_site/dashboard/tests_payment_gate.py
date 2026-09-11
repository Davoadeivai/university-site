"""بازگشت از درگاه، و ترتیب اقساط.

هر دو جایی‌اند که پول در میان است و خطایشان بی‌صدا می‌ماند: دانشجو
پرداخت می‌کند و سامانه چیزی ثبت نمی‌کند.
"""
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from dashboard.models import Payment, Semester


def _semester():
    return Semester.objects.create(
        name='نیم‌سال آزمایشی', academic_year='۱۴۰۵-۱۴۰۶',
        semester_type='fall', is_active=True,
        start_date=date(2026, 9, 22), end_date=date(2027, 1, 20))


def _student(username):
    from accounts.models import UserProfile

    user = User.objects.create_user(username, password='x')
    UserProfile.objects.get_or_create(
        user=user, defaults={'role': 'student'})
    UserProfile.objects.filter(user=user).update(role='student')
    return user


@override_settings(ALLOW_MOCK_PAYMENT=True, PAYMENT_GATEWAY='mock')
class TheBankCanReturnWithoutASessionTests(TestCase):
    """رفت‌وبرگشت درگاه چند دقیقه است و جلسه ممکن است نماند.

    با \u200E@login_required\u200E آن بازگشت به صفحهٔ ورود می‌رفت و پرداخت
    هیچ‌وقت تأیید نمی‌شد: پول از حساب دانشجو کم شده، قسط همچنان
    «در انتظار».
    """

    def setUp(self):
        self.user = _student('9911111')
        self.semester = _semester()
        self.payment = Payment.objects.create(
            student=self.user, payment_type='tuition', amount=1000000,
            semester=self.semester, status='pending',
            installment_no=1, installment_stage='initial',
            authority='MOCK-ABCDEF0123456789')
        self.url = reverse('dashboard:payment_callback')

    def _callback(self, **params):
        return self.client.get(self.url, params, follow=True)

    def test_a_signed_out_return_still_settles_the_payment(self):
        self._callback(Authority=self.payment.authority, Status='OK')
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')

    def test_the_student_is_told_to_sign_in_afterwards(self):
        response = self._callback(
            Authority=self.payment.authority, Status='OK')
        self.assertContains(response, 'پرداخت شما ثبت شد')

    def test_a_signed_in_return_works_as_before(self):
        self.client.force_login(self.user)
        self._callback(Authority=self.payment.authority, Status='OK',
                       payment_id=self.payment.pk)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')

    def test_a_wrong_authority_settles_nothing(self):
        self._callback(Authority='MOCK-NOTTHISONE', Status='OK')
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    def test_an_empty_authority_does_not_grab_someone_elses_payment(self):
        """ردیف‌هایی که هنوز به درگاه نرفته‌اند همگی authority خالی دارند.

        فیلتر با رشتهٔ خالی یکی از آن‌ها را — متعلق به هر کسی —
        برمی‌گرداند.
        """
        other = Payment.objects.create(
            student=_student('9922222'), payment_type='tuition',
            amount=500000, semester=self.semester, status='pending',
            installment_no=1, installment_stage='initial')

        self._callback(Authority='', Status='OK')
        other.refresh_from_db()
        self.assertEqual(other.status, 'pending')

    def test_another_students_session_cannot_claim_it(self):
        """کارمند یا دانشجوی دیگر نباید پرداخت کسی را دست‌کاری کند."""
        self.client.force_login(_student('9933333'))
        self._callback(Authority=self.payment.authority, Status='OK',
                       payment_id=self.payment.pk)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    def test_a_cancelled_payment_is_not_marked_paid(self):
        self._callback(Authority=self.payment.authority, Status='NOK')
        self.payment.refresh_from_db()
        self.assertNotEqual(self.payment.status, 'paid')


@override_settings(ALLOW_MOCK_PAYMENT=True, PAYMENT_GATEWAY='mock')
class ARefundedInstallmentDoesNotLockTheRestTests(TestCase):
    """مسترد، «پرداخت‌نشده» نیست.

    پیش از این فقط \u200Epaid\u200E استثنا بود، پس قسطی که مسترد شده بود اقساط
    بعدی را برای همیشه قفل می‌کرد و دانشجو راهی جز دست‌کاری دستی در
    پنل نداشت.
    """

    def setUp(self):
        self.user = _student('9944444')
        self.client.force_login(self.user)
        self.semester = _semester()

        self.first = Payment.objects.create(
            student=self.user, payment_type='tuition', amount=400000,
            semester=self.semester, status='refunded',
            installment_no=1, installment_stage='initial')
        self.second = Payment.objects.create(
            student=self.user, payment_type='tuition', amount=300000,
            semester=self.semester, status='pending',
            installment_no=2, installment_stage='mid')

    def _start(self):
        return self.client.get(
            reverse('dashboard:payment_start', args=[self.second.pk]),
            follow=True)

    def test_the_next_installment_can_be_started(self):
        self._start()
        self.second.refresh_from_db()
        self.assertTrue(self.second.authority)

    def test_it_does_not_complain_about_earlier_installments(self):
        response = self._start()
        self.assertNotContains(response, 'ابتدا اقساط قبلی')

    def test_a_genuinely_unpaid_earlier_installment_still_blocks(self):
        """قاعده سرِ جایش است؛ فقط مسترد از آن بیرون آمد."""
        self.first.status = 'pending'
        self.first.save(update_fields=['status'])

        response = self._start()
        self.assertContains(response, 'ابتدا اقساط قبلی')
        self.second.refresh_from_db()
        self.assertFalse(self.second.authority)
