"""حذف کاربر از پنل — و اینکه چرا گاهی نباید انجام شود.

دکمهٔ «حذف» برای هر ردیف رندر می‌شد، حتی برای حسابی که اجازه‌اش را
نداشت. کلیک روی آن یک صفحهٔ ۴۰۳ می‌آورد و مدیر سایت فقط می‌دید که
«نمی‌شود»، بی‌آنکه بداند چرا.
"""
from django.contrib.auth.models import Permission, User
from django.test import TestCase

from accounts.models import UserProfile


def _allow(user, *codenames):
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get(codename=codename))


class DeletingAUserWorksTests(TestCase):
    """آنچه از قبل کار می‌کرد باید کار کند."""

    def setUp(self):
        self.boss = User.objects.create_superuser(
            'modirkol', 'b@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.boss)

    def _target(self, name='hadaf'):
        return User.objects.create_user(name, '%s@aab.ac.ir' % name,
                                        'Str0ng!Pass2026')

    def test_a_plain_user_is_deleted(self):
        target = self._target()
        self.client.post('/admin/auth/user/%d/delete/' % target.pk,
                         {'post': 'yes'}, follow=True)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())

    def test_a_user_with_a_profile_is_deleted(self):
        target = self._target()
        UserProfile.objects.filter(user=target).delete()
        UserProfile.objects.create(user=target, role='student',
                                   student_id='990')
        self.client.post('/admin/auth/user/%d/delete/' % target.pk,
                         {'post': 'yes'}, follow=True)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())

    def test_the_bulk_action_deletes(self):
        target = self._target()
        self.client.post('/admin/auth/user/', {
            'action': 'delete_selected_users',
            '_selected_action': [str(target.pk)],
            'post': 'yes',
        }, follow=True)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())

    def test_the_button_is_shown_when_it_works(self):
        self._target()
        html = self.client.get('/admin/auth/user/').content.decode()
        self.assertIn('btn-danger', html)
        self.assertIn('/delete/', html)


class TheButtonTellsTheTruthTests(TestCase):
    """دکمه‌ای که کار نمی‌کند نباید دیده شود."""

    def setUp(self):
        self.staff = User.objects.create_user(
            'karmand', 'k@aab.ac.ir', 'Str0ng!Pass2026', is_staff=True)
        _allow(self.staff, 'view_user', 'change_user')
        self.client.force_login(self.staff)
        User.objects.create_user('hadaf2', 'h2@aab.ac.ir', 'Str0ng!Pass2026')

    def test_no_delete_button_without_the_permission(self):
        html = self.client.get('/admin/auth/user/').content.decode()
        self.assertNotIn('btn-danger', html)

    def test_the_reason_is_written_down(self):
        html = self.client.get('/admin/auth/user/').content.decode()
        self.assertIn('اجازهٔ حذف کاربر ندارد', html)


class YouCannotDeleteYourselfTests(TestCase):
    """با حذف حساب خودتان، همان لحظه از پنل بیرون می‌افتید."""

    def setUp(self):
        self.boss = User.objects.create_superuser(
            'modir1', 'm1@aab.ac.ir', 'Str0ng!Pass2026')
        User.objects.create_superuser('modir2', 'm2@aab.ac.ir',
                                      'Str0ng!Pass2026')
        self.client.force_login(self.boss)

    def test_the_confirmation_page_refuses(self):
        response = self.client.get(
            '/admin/auth/user/%d/delete/' % self.boss.pk)
        self.assertEqual(response.status_code, 403)

    def test_the_post_refuses(self):
        self.client.post('/admin/auth/user/%d/delete/' % self.boss.pk,
                         {'post': 'yes'}, follow=True)
        self.assertTrue(User.objects.filter(pk=self.boss.pk).exists())

    def test_the_row_explains_why(self):
        html = self.client.get('/admin/auth/user/').content.decode()
        self.assertIn('حساب خودِ شماست', html)

    def test_the_bulk_action_skips_it(self):
        self.client.post('/admin/auth/user/', {
            'action': 'delete_selected_users',
            '_selected_action': [str(self.boss.pk)],
            'post': 'yes',
        }, follow=True)
        self.assertTrue(User.objects.filter(pk=self.boss.pk).exists())


class TheLastSuperuserIsKeptTests(TestCase):
    """با حذفش هیچ‌کس دیگر به پنل راه ندارد."""

    def setUp(self):
        self.only = User.objects.create_superuser(
            'tanha', 't@aab.ac.ir', 'Str0ng!Pass2026')
        self.deleter = User.objects.create_user(
            'hazefkol', 'd@aab.ac.ir', 'Str0ng!Pass2026', is_staff=True)
        _allow(self.deleter, 'view_user', 'change_user', 'delete_user')
        self.client.force_login(self.deleter)

    def test_it_cannot_be_deleted(self):
        response = self.client.get(
            '/admin/auth/user/%d/delete/' % self.only.pk)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.only.pk).exists())

    def test_a_second_superuser_makes_the_first_deletable(self):
        User.objects.create_superuser('dovom', 'd2@aab.ac.ir',
                                      'Str0ng!Pass2026')
        self.client.force_login(User.objects.get(username='dovom'))
        self.client.post('/admin/auth/user/%d/delete/' % self.only.pk,
                         {'post': 'yes'}, follow=True)
        self.assertFalse(User.objects.filter(pk=self.only.pk).exists())


class OnlyASuperuserRemovesASuperuserTests(TestCase):

    def setUp(self):
        User.objects.create_superuser('kol1', 'k1@aab.ac.ir',
                                      'Str0ng!Pass2026')
        self.other = User.objects.create_superuser(
            'kol2', 'k2@aab.ac.ir', 'Str0ng!Pass2026')
        self.staff = User.objects.create_user(
            'karmand2', 'k@aab.ac.ir', 'Str0ng!Pass2026', is_staff=True)
        _allow(self.staff, 'view_user', 'change_user', 'delete_user')
        self.client.force_login(self.staff)

    def test_a_staff_member_may_not(self):
        response = self.client.get(
            '/admin/auth/user/%d/delete/' % self.other.pk)
        self.assertEqual(response.status_code, 403)

    def test_a_staff_member_may_still_delete_a_normal_user(self):
        target = User.objects.create_user('addi', 'a@aab.ac.ir',
                                          'Str0ng!Pass2026')
        self.client.post('/admin/auth/user/%d/delete/' % target.pk,
                         {'post': 'yes'}, follow=True)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())
