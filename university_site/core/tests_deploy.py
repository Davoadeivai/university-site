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
