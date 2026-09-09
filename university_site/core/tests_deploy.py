"""دیپلوی باید بدون ترمینال کار کند."""
import ast
import io
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


def _source():
    return io.open(Path(settings.BASE_DIR).parent / 'deploy.py',
                   encoding='utf-8').read()


class DeployPullsItsOwnCodeTests(SimpleTestCase):
    """ترمینال cPanel روی این هاست در دسترس نیست."""

    def test_the_script_parses(self):
        ast.parse(_source())

    def test_it_pulls_before_copying(self):
        """کپی کد قدیمی و بعد کشیدن کد تازه، ترتیب بی‌فایده‌ای است."""
        source = _source()
        tree = ast.parse(source)
        main = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'main')
        calls = [node.func.id for node in ast.walk(main)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        self.assertIn('pull', calls)
        self.assertIn('copy_tree', calls)
        self.assertLess(calls.index('pull'), calls.index('copy_tree'))

    def test_the_pull_is_fast_forward_only(self):
        """merge خودکار روی سرور یعنی کامیت مرج بی‌صاحب."""
        body = _source().split('def pull')[1].split('\ndef ')[0]
        self.assertIn("'pull'", body)
        self.assertIn("'--ff-only'", body)

    def test_a_failed_pull_does_not_stop_the_deploy(self):
        """اگر گیت نبود، باید با کد موجود ادامه دهد، نه اینکه بایستد."""
        body = _source().split('def pull')[1].split('\ndef ')[0]
        self.assertIn('except', body)
        self.assertNotIn('raise', body)
        self.assertNotIn('sys.exit', body)

    def test_it_says_so_when_the_pull_fails(self):
        """سکوت یعنی کاربر فکر می‌کند کد تازه رفته، در حالی که نرفته."""
        body = _source().split('def pull')[1].split('\ndef ')[0]
        self.assertIn('returncode', body)
        self.assertIn('!!', body)

    def test_the_pull_cannot_hang_the_deploy(self):
        body = _source().split('def pull')[1].split('\ndef ')[0]
        self.assertIn('timeout=', body)

    def test_the_instructions_no_longer_demand_a_terminal(self):
        doc = ast.get_docstring(ast.parse(_source())) or ''
        self.assertIn('Execute python script', doc)
        self.assertNotIn('اول «Update from Remote» را بزنید', doc)


def _run_deploy_source():
    return io.open(Path(settings.BASE_DIR) / 'run_deploy.py',
                   encoding='utf-8').read()


def _content_commands():
    """فهرست CONTENT_COMMANDS، بی‌آنکه اسکریپت اجرا شود."""
    tree = ast.parse(_run_deploy_source())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'CONTENT_COMMANDS':
                return [item.value for item in node.value.elts]
    raise AssertionError('CONTENT_COMMANDS پیدا نشد')


class TheRosterIsRestoredOnEveryDeployTests(SimpleTestCase):
    """صفحه‌های ارکان موسسه و هیئت علمی از سند «افراد موسسه» پر می‌شوند.

    این دستور روی دیپلوی اجرا نمی‌شد، پس هر پایگاه داده‌ای که دستی
    روی آن اجرا نشده بود فهرستی ناقص یا کهنه نشان می‌داد — و نفرات
    ارکان با آنچه سند می‌گوید فرق داشتند.
    """

    def test_the_people_document_is_seeded(self):
        self.assertIn('seed_directory', _content_commands())

    def test_it_runs_before_the_group_heads(self):
        """مدیران گروه از همین فهرست خوانده می‌شوند."""
        commands = _content_commands()
        self.assertLess(commands.index('seed_directory'),
                        commands.index('set_group_heads'))

    def test_no_destructive_flag_is_passed(self):
        """\u200E--prune\u200E و \u200E--trust-document\u200E ویرایش‌های پنل را می‌برند."""
        source = _run_deploy_source()
        for flag in ('--prune', '--trust-document', '--refresh-photos'):
            self.assertNotIn(flag, source)

    def test_every_listed_command_exists(self):
        from django.core.management import get_commands

        available = get_commands()
        for name in _content_commands():
            self.assertIn(name, available, name)


class TheSeedDocumentIsCompleteTests(SimpleTestCase):
    """سند افراد باید همان تعدادی را داشته باشد که موسسه اعلام کرده."""

    def _people(self):
        import json

        path = (Path(settings.BASE_DIR) / 'directory' / 'seed_data' /
                'people.json')
        return json.loads(path.read_text(encoding='utf-8'))

    def test_the_two_bodies_are_there(self):
        people = self._people()
        self.assertEqual(len(people['founder']), 6)
        self.assertEqual(len(people['trustee']), 8)

    def test_the_teaching_staff_are_there(self):
        people = self._people()
        self.assertEqual(len(people['faculty']), 12)
        self.assertEqual(len(people['group_head']), 10)
        self.assertEqual(len(people['lecturer']), 43)

    def test_nobody_is_nameless(self):
        """دو نوشتار در سند هست و مدل هر دو را می‌پذیرد.

        ارکان و مدرسین نام کامل می‌دهند؛ کارکنان نام و نام خانوادگی
        جدا، و \u200EDirectoryPerson.save\u200E آن دو را به هم می‌چسباند.
        """
        people = self._people()
        for category in ('founder', 'trustee', 'faculty', 'group_head',
                         'lecturer', 'staff'):
            for row in people[category]:
                name = (row.get('full_name')
                        or '%s %s' % (row.get('first_name', ''),
                                      row.get('last_name', '')))
                self.assertTrue(name.strip(), '%s: ردیف بی‌نام' % category)
