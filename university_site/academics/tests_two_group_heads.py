"""یک گروه، دو مدیر.

«حسابداری» و «مدیریت صنعتی و مالی» هرکدام دو مدیر دارند. فیلدهای
تکیِ روی خود گروه فقط یک نفر جا می‌دادند: نفر دوم نه عکسی داشت، نه
مرتبه‌ای، نه راه تماسی، و در پنل جایی برای ثبتش نبود.
"""
from django.contrib.auth.models import User
from django.test import TestCase

from academics.models import AcademicGroup, Department, GroupHead
from faculty.models import Professor


class TwoHeadsFitInAGroupTests(TestCase):

    def setUp(self):
        self.faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-2h', order=1, is_active=True)
        self.group = AcademicGroup.objects.create(
            department=self.faculty, name='گروه حسابداری', slug='hesab-2h',
            is_active=True)

    def _add(self, name, **kwargs):
        return GroupHead.objects.create(group=self.group, name=name, **kwargs)

    def test_both_are_listed_in_order(self):
        self._add('سجاد سالاری', order=1)
        self._add('مسعود باباخانی', order=2)
        self.assertEqual([card['name'] for card in self.group.heads_list],
                         ['سجاد سالاری', 'مسعود باباخانی'])

    def test_each_keeps_its_own_photo(self):
        self._add('اول', order=1, photo='groups/heads/a.jpg')
        self._add('دوم', order=2, photo='groups/heads/b.jpg')
        images = [card['image'].name for card in self.group.heads_list]
        self.assertEqual(images, ['groups/heads/a.jpg', 'groups/heads/b.jpg'])

    def test_each_keeps_its_own_contacts(self):
        self._add('اول', order=1, phone='011-1', email='a@aab.ac.ir')
        self._add('دوم', order=2, phone='011-2', email='b@aab.ac.ir')
        cards = self.group.heads_list
        self.assertEqual([card['phone'] for card in cards], ['011-1', '011-2'])
        self.assertEqual([card['email'] for card in cards],
                         ['a@aab.ac.ir', 'b@aab.ac.ir'])

    def test_a_note_tells_them_apart(self):
        self._add('اول', order=1, note='ارشد')
        self._add('دوم', order=2)
        self.assertEqual([card['note'] for card in self.group.heads_list],
                         ['ارشد', ''])

    def test_a_prefix_belongs_to_the_person_not_the_group(self):
        self._add('سالاری', order=1, honorific='دکتر')
        self._add('باباخانی', order=2, honorific='مهندس')
        self.assertEqual([card['name'] for card in self.group.heads_list],
                         ['دکتر سالاری', 'مهندس باباخانی'])

    def test_a_prefix_is_not_doubled(self):
        self._add('دکتر سالاری', honorific='دکتر')
        self.assertEqual(self.group.heads_list[0]['name'], 'دکتر سالاری')

    def test_a_linked_professor_brings_photo_and_rank(self):
        professor = Professor.objects.create(
            first_name='سجاد', last_name='سالاری', rank='assistant',
            is_active=True, email='s@aab.ac.ir')
        head = GroupHead.objects.create(group=self.group, professor=professor)
        card = self.group.heads_list[0]
        self.assertEqual(card['name'], 'سجاد سالاری')
        self.assertEqual(card['rank'], professor.get_rank_display())
        self.assertEqual(card['email'], 's@aab.ac.ir')
        self.assertTrue(card['page'])
        self.assertEqual(head.group_id, self.group.pk)

    def test_a_typed_name_beats_the_linked_one(self):
        professor = Professor.objects.create(
            first_name='سجاد', last_name='سالاری', is_active=True)
        self._add('نام دیگر', professor=professor)
        self.assertEqual(self.group.heads_list[0]['name'], 'نام دیگر')

    def test_an_inactive_row_is_left_out(self):
        self._add('اول', order=1)
        self._add('دوم', order=2, is_active=False)
        self.assertEqual([card['name'] for card in self.group.heads_list],
                         ['اول'])

    def test_a_nameless_row_is_left_out(self):
        self._add('', order=1)
        self.assertEqual(self.group.heads_list, [])

    def test_the_label_follows_the_count(self):
        self._add('اول', order=1)
        self.assertEqual(self.group.heads_label, 'مدیر گروه')
        self._add('دوم', order=2)
        self.assertEqual(self.group.heads_label, 'مدیران گروه')


class OldSingleFieldsStillWorkTests(TestCase):
    """داده‌ای که پیش از این ثبت شده نباید ناپدید شود."""

    def setUp(self):
        faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-old', order=1, is_active=True)
        self.group = AcademicGroup.objects.create(
            department=faculty, name='گروه روان‌شناسی', slug='ravan-old',
            is_active=True, head='حسینعلی قربانی', head_honorific='دکتر')

    def test_the_single_head_becomes_the_only_card(self):
        self.assertEqual([card['name'] for card in self.group.heads_list],
                         ['دکتر حسینعلی قربانی'])

    def test_a_row_takes_over_when_one_exists(self):
        """دو منبع برای یک چیز، دیر یا زود با هم اختلاف پیدا می‌کنند."""
        GroupHead.objects.create(group=self.group, name='مدیر تازه')
        self.assertEqual([card['name'] for card in self.group.heads_list],
                         ['مدیر تازه'])

    def test_an_empty_group_says_nothing(self):
        self.group.head = ''
        self.group.head_honorific = ''
        self.group.save()
        self.assertEqual(self.group.heads_list, [])


class BothHeadsReachThePagesTests(TestCase):

    def setUp(self):
        faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-pg', order=1, is_active=True)
        self.group = AcademicGroup.objects.create(
            department=faculty, name='گروه حسابداری', slug='hesab-pg',
            is_active=True)
        GroupHead.objects.create(group=self.group, name='سجاد سالاری',
                                 phone='011-1', order=1)
        GroupHead.objects.create(group=self.group, name='مسعود باباخانی',
                                 phone='011-2', order=2)

    def test_the_group_page_shows_both(self):
        html = self.client.get(
            self.group.get_absolute_url()).content.decode()
        self.assertIn('سجاد سالاری', html)
        self.assertIn('مسعود باباخانی', html)

    def test_the_group_page_gives_each_a_photo_frame(self):
        html = self.client.get(
            self.group.get_absolute_url()).content.decode()
        self.assertEqual(html.count('grp-lead-photo'), 2)

    def test_the_heads_page_shows_both(self):
        from django.urls import reverse

        html = self.client.get(
            reverse('academics:group_heads')).content.decode()
        self.assertIn('سجاد سالاری', html)
        self.assertIn('مسعود باباخانی', html)

    def test_each_phone_sits_with_its_own_name(self):
        from django.urls import reverse

        html = self.client.get(
            reverse('academics:group_heads')).content.decode()
        first = html.split('سجاد سالاری')[1].split('مسعود باباخانی')[0]
        self.assertIn('011-1', first)
        self.assertNotIn('011-2', first)

    def test_the_groups_list_shows_both(self):
        from django.urls import reverse

        html = self.client.get(
            reverse('academics:groups_list')).content.decode()
        self.assertIn('سجاد سالاری', html)
        self.assertIn('مسعود باباخانی', html)


class TheHeadCanBeEditedAndRemovedTests(TestCase):
    """موسسه نمی‌توانست مدیر یک گروه را ویرایش یا حذف کند."""

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'modirgrp', 'g@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.staff)
        faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-ed', order=1, is_active=True)
        self.group = AcademicGroup.objects.create(
            department=faculty, name='گروه مدیریت صنعتی و مالی',
            slug='sanati-ed', is_active=True, head='مدیر پیشین')

    def test_the_panel_offers_a_row_per_head(self):
        html = self.client.get(
            '/admin/academics/academicgroup/%d/change/' % self.group.pk
        ).content.decode()
        self.assertIn('مدیران این گروه', html)
        self.assertIn('group_heads', html)

    def test_editing_a_head_locks_the_group(self):
        """وگرنه به‌روزرسانی بعدی تصمیم مدیر سایت را بازمی‌نویسد."""
        from academics.admin import AcademicGroupAdmin

        self.assertIn('head', AcademicGroupAdmin.HEAD_FIELDS)
        self.assertIn('head_professor', AcademicGroupAdmin.HEAD_FIELDS)

    def test_the_clearing_action_empties_everything(self):
        self.group.head_honorific = 'دکتر'
        self.group.head_phone = '011-9'
        self.group.save()
        response = self.client.post('/admin/academics/academicgroup/', {
            'action': 'clear_head',
            '_selected_action': [str(self.group.pk)],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.group.refresh_from_db()
        self.assertEqual(self.group.head, '')
        self.assertEqual(self.group.head_honorific, '')
        self.assertEqual(self.group.head_phone, '')
        self.assertEqual(self.group.heads_list, [])

    def test_clearing_also_locks_it(self):
        self.client.post('/admin/academics/academicgroup/', {
            'action': 'clear_head',
            '_selected_action': [str(self.group.pk)],
        }, follow=True)
        self.group.refresh_from_db()
        self.assertTrue(self.group.head_locked)

    def test_the_lock_is_visible_in_the_list(self):
        from academics.admin import AcademicGroupAdmin

        self.assertIn('head_locked', AcademicGroupAdmin.list_display)
        self.assertIn('head_locked', AcademicGroupAdmin.list_editable)
