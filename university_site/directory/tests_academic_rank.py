"""مرتبهٔ علمی — «دانشیار» را باید بشود نوشت.

سند موسسه فقط مدرک داشت، پس مرتبه از مدرک حدس زده می‌شد: دکتری یعنی
استادیار. برای بیشتر افراد درست بود و برای دانشیار و استاد تمام غلط،
و هیچ کادری هم برای اصلاحش نبود.
"""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from directory.models import DirectoryPerson
from faculty.models import Professor


def _import(*args):
    call_command('import_from_directory', *args, stdout=StringIO(),
                 stderr=StringIO())


class TheDirectoryCanStateARankTests(TestCase):

    def test_the_field_offers_associate_professor(self):
        values = dict(DirectoryPerson.RANK_CHOICES)
        self.assertEqual(values['associate'], 'دانشیار')
        self.assertEqual(values['professor'], 'استاد تمام')

    def test_it_may_stay_empty(self):
        person = DirectoryPerson(category='faculty', full_name='بی‌مرتبه')
        person.full_clean(exclude=['created_at', 'updated_at'])

    def test_the_panel_shows_it(self):
        staff = User.objects.create_superuser(
            'modirrank', 'r@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(staff)
        person = DirectoryPerson.objects.create(
            category='faculty', full_name='حسن فارسیجانی')
        html = self.client.get(
            '/admin/directory/directoryperson/%d/change/' % person.pk
        ).content.decode()
        self.assertIn('name="academic_rank"', html)
        self.assertIn('دانشیار', html)

    def test_it_is_editable_from_the_list(self):
        from directory.admin import DirectoryPersonAdmin

        self.assertIn('academic_rank', DirectoryPersonAdmin.list_editable)


class TheStatedRankBeatsTheGuessTests(TestCase):
    """حدس فقط وقتی کار می‌کند که موسسه چیزی نگفته باشد."""

    def _person(self, **kwargs):
        kwargs.setdefault('category', 'faculty')
        kwargs.setdefault('full_name', 'حسن فارسیجانی')
        kwargs.setdefault('degree', 'phd')
        kwargs.setdefault('is_active', True)
        return DirectoryPerson.objects.create(**kwargs)

    def _professor(self):
        return Professor.objects.get(last_name='فارسیجانی')

    def test_a_doctorate_alone_still_guesses_assistant(self):
        self._person()
        _import()
        self.assertEqual(self._professor().rank, 'assistant')

    def test_a_stated_rank_is_used_instead(self):
        self._person(academic_rank='associate')
        _import()
        self.assertEqual(self._professor().rank, 'associate')
        self.assertEqual(self._professor().get_rank_display(), 'دانشیار')

    def test_it_corrects_a_record_the_guess_already_wrote(self):
        """اصلاح در پنل باید به پروندهٔ استاد برسد، نه اینکه بماند."""
        person = self._person()
        _import()
        self.assertEqual(self._professor().rank, 'assistant')
        person.academic_rank = 'associate'
        person.save(update_fields=['academic_rank'])
        _import()
        self.assertEqual(self._professor().rank, 'associate')

    def test_a_rank_the_admin_set_by_hand_is_not_undone(self):
        """اگر سند چیزی نگوید، دستِ ادمین دست‌نخورده می‌ماند."""
        self._person()
        _import()
        professor = self._professor()
        professor.rank = 'professor'
        professor.save(update_fields=['rank'])
        _import()
        self.assertEqual(self._professor().rank, 'professor')

    def test_the_full_professor_rank_also_travels(self):
        self._person(academic_rank='professor')
        _import()
        self.assertEqual(self._professor().get_rank_display(), 'استاد تمام')
