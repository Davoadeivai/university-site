"""ویرایش هیئت امنا در پنل باید بماند.

نام و سمتِ هر عضو با هر اجرای `seed_directory` از روی سند بازنویسی
می‌شد؛ یعنی هر اصلاحی که موسسه در پنل انجام می‌داد بی‌صدا برمی‌گشت
و کسی هم نمی‌گفت چرا.
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import BoardMember


def _seed(*args):
    call_command('seed_directory', *args, stdout=StringIO(), stderr=StringIO())


class AnEditSurvivesTheSeederTests(TestCase):

    def setUp(self):
        _seed()
        self.member = BoardMember.objects.filter(
            board_type='trustee').order_by('order').first()
        self.assertIsNotNone(self.member, 'سند هیچ عضو هیئت امنایی ندارد')

    def test_a_renamed_member_keeps_the_new_name(self):
        self.member.full_name = 'دکتر نام اصلاح‌شده'
        self.member.save()
        _seed()
        self.member.refresh_from_db()
        self.assertEqual(self.member.full_name, 'دکتر نام اصلاح‌شده')

    def test_a_changed_title_stays_changed(self):
        self.member.title = 'سمت تازه'
        self.member.save()
        _seed()
        self.member.refresh_from_db()
        self.assertEqual(self.member.title, 'سمت تازه')

    def test_the_change_reaches_the_public_page(self):
        self.member.full_name = 'دکتر نام اصلاح‌شده'
        self.member.save()
        _seed()
        html = self.client.get(
            reverse('core:board_trustees')).content.decode()
        self.assertIn('دکتر نام اصلاح‌شده', html)

    def test_an_empty_field_is_still_filled_from_the_document(self):
        """محافظت از ویرایش نباید یعنی رهاکردن جای خالی."""
        self.member.title = ''
        self.member.save()
        _seed()
        self.member.refresh_from_db()
        self.assertTrue(self.member.title)

    def test_the_document_can_still_win_when_asked(self):
        original = self.member.full_name
        self.member.full_name = 'نام موقت'
        self.member.save()
        _seed('--trust-document')
        self.member.refresh_from_db()
        self.assertEqual(self.member.full_name, original)

    def test_a_renamed_member_is_not_duplicated(self):
        """ریشهٔ همان «ویرایش اعمال نمی‌شود»: نام قدیمی دوباره سبز می‌شد."""
        before = BoardMember.objects.filter(board_type='trustee').count()
        self.member.full_name = 'دکتر نام تازه'
        self.member.save()
        _seed()
        self.assertEqual(
            BoardMember.objects.filter(board_type='trustee').count(), before)

    def test_running_it_twice_makes_no_duplicates(self):
        before = BoardMember.objects.filter(board_type='trustee').count()
        _seed()
        _seed()
        self.assertEqual(
            BoardMember.objects.filter(board_type='trustee').count(), before)

    def test_a_deactivated_member_is_brought_back(self):
        """کسی که در سند هست باید روی سایت دیده شود."""
        self.member.is_active = False
        self.member.save()
        _seed()
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)


class ThePanelSaysWhichListDrivesThePageTests(TestCase):
    """دو فهرست برای یک عده آدم؛ بدون توضیح، ویرایش در آن یکی بی‌اثر است."""

    def test_the_board_admin_says_it_drives_the_pages(self):
        from core.admin import BoardMemberAdmin

        self.assertIn('هیات امنا', str(BoardMemberAdmin.fieldsets))

    def test_the_directory_admin_points_at_the_board_list(self):
        from directory.admin import DirectoryPersonAdmin

        note = DirectoryPersonAdmin.fieldsets[0][1]['description']
        self.assertIn('هیات امنا', note)
        self.assertIn('نه از اینجا', note)
