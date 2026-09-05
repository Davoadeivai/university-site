"""لاگ ادمین نباید جلوی حذف کاربر را بگیرد.

پیام «حساب شما دسترسی لازم برای حذف اشیای از انواع زیر را ندارد:
مورد اتفاقات» برای همه می‌آمد — حتی مدیر کل — چون لاگ فقط‌خواندنی
بود و جنگو هنگام حذف کاربر، اجازهٔ حذفِ لاگ‌های او را هم می‌پرسد.
"""
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase


def _log(user, count=1):
    content_type = ContentType.objects.get_for_model(User)
    for index in range(count):
        LogEntry.objects.create(
            user=user, content_type=content_type, object_id=str(user.pk),
            object_repr='کاری در پنل %d' % index, action_flag=CHANGE,
            change_message='[]')


class AUserWithAdminHistoryIsDeletableTests(TestCase):

    def setUp(self):
        self.boss = User.objects.create_superuser(
            'raees', 'r@aab.ac.ir', 'Str0ng!Pass2026')
        User.objects.create_superuser('raees2', 'r2@aab.ac.ir',
                                      'Str0ng!Pass2026')
        self.client.force_login(self.boss)
        self.samad = User.objects.create_user(
            'samad', 's@aab.ac.ir', 'Str0ng!Pass2026', is_staff=True)
        _log(self.samad, 3)

    def test_the_confirmation_page_no_longer_refuses(self):
        response = self.client.get(
            '/admin/auth/user/%d/delete/' % self.samad.pk)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn('دسترسی لازم برای حذف', body)

    def test_the_user_is_actually_deleted(self):
        self.client.post('/admin/auth/user/%d/delete/' % self.samad.pk,
                         {'post': 'yes'}, follow=True)
        self.assertFalse(User.objects.filter(pk=self.samad.pk).exists())

    def test_their_log_rows_go_with_them(self):
        self.client.post('/admin/auth/user/%d/delete/' % self.samad.pk,
                         {'post': 'yes'}, follow=True)
        self.assertEqual(LogEntry.objects.filter(user=self.samad).count(), 0)

    def test_other_peoples_log_rows_stay(self):
        """فقط لاگ‌های خودِ کاربرِ حذف‌شده می‌روند.

        شمار لاگِ مدیر یکی بیشتر می‌شود، نه کمتر: خودِ همین حذف هم
        به نام او ثبت می‌شود.
        """
        _log(self.boss, 2)
        self.client.post('/admin/auth/user/%d/delete/' % self.samad.pk,
                         {'post': 'yes'}, follow=True)
        self.assertGreaterEqual(
            LogEntry.objects.filter(user=self.boss).count(), 2)

    def test_the_deletion_itself_is_recorded(self):
        from django.contrib.admin.models import DELETION

        self.client.post('/admin/auth/user/%d/delete/' % self.samad.pk,
                         {'post': 'yes'}, follow=True)
        self.assertTrue(LogEntry.objects.filter(
            user=self.boss, action_flag=DELETION,
            object_repr__icontains='samad').exists())

    def test_the_bulk_action_works_too(self):
        self.client.post('/admin/auth/user/', {
            'action': 'delete_selected_users',
            '_selected_action': [str(self.samad.pk)],
            'post': 'yes',
        }, follow=True)
        self.assertFalse(User.objects.filter(pk=self.samad.pk).exists())


class TheHistoryStaysReadOnlyTests(TestCase):
    """باز کردن راه آبشاری نباید یعنی باز کردن راه دست‌کاری."""

    def setUp(self):
        self.boss = User.objects.create_superuser(
            'raees3', 'r3@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.boss)
        _log(self.boss)
        self.row = LogEntry.objects.first()

    def test_a_log_row_cannot_be_deleted_directly(self):
        response = self.client.get(
            '/admin/admin/logentry/%d/delete/' % self.row.pk)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(LogEntry.objects.filter(pk=self.row.pk).exists())

    def test_the_bulk_delete_action_is_not_offered(self):
        html = self.client.get('/admin/admin/logentry/').content.decode()
        self.assertNotIn('delete_selected', html)

    def test_a_log_row_cannot_be_edited(self):
        from core.admin_logentry import LogEntryAdmin

        admin = LogEntryAdmin(LogEntry, None)
        self.assertFalse(admin.has_change_permission(None))
        self.assertFalse(admin.has_add_permission(None))


class OnlyASuperuserUnlocksTheCascadeTests(TestCase):

    def test_a_staff_member_is_still_told_why(self):
        """کارمند نباید بتواند تاریخچهٔ کسی را از بین ببرد."""
        staff = User.objects.create_user(
            'karmand3', 'k@aab.ac.ir', 'Str0ng!Pass2026', is_staff=True)
        for codename in ('view_user', 'change_user', 'delete_user'):
            staff.user_permissions.add(
                Permission.objects.get(codename=codename))
        target = User.objects.create_user('hadaf9', 'h@aab.ac.ir',
                                          'Str0ng!Pass2026', is_staff=True)
        _log(target)
        self.client.force_login(staff)
        body = self.client.get(
            '/admin/auth/user/%d/delete/' % target.pk).content.decode()
        self.assertIn('دسترسی لازم برای حذف', body)

    def test_a_staff_member_may_still_delete_a_user_with_no_history(self):
        staff = User.objects.create_user(
            'karmand4', 'k4@aab.ac.ir', 'Str0ng!Pass2026', is_staff=True)
        for codename in ('view_user', 'change_user', 'delete_user'):
            staff.user_permissions.add(
                Permission.objects.get(codename=codename))
        target = User.objects.create_user('hadaf10', 'h10@aab.ac.ir',
                                          'Str0ng!Pass2026')
        self.client.force_login(staff)
        self.client.post('/admin/auth/user/%d/delete/' % target.pk,
                         {'post': 'yes'}, follow=True)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())
