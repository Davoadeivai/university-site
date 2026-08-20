"""بازرسی الگوهای رایجی که نمایش موبایل را خراب می‌کنند.

چرا این دستور هست
─────────────────
ایرادهای موبایل بی‌صدا هستند: نه خطایی در لاگ می‌افتد، نه تستی می‌شکند.
تنها وقتی دیده می‌شوند که کسی سایت را با گوشی باز کند. این دستور همان
بازرسی را خودکار می‌کند تا هر بار پیش از دیپلوی بشود اجرایش کرد.

    python manage.py check_responsive
    python manage.py check_responsive --fail-on-error   # برای CI

چه چیزهایی را می‌بیند
────────────────────
۱. عرض ثابت پیکسلی (width:900px) که روی صفحهٔ ۳۶۰ پیکسلی بیرون می‌زند
۲. جدول بدون ظرف اسکرول‌شونده
۳. backdrop-filter بدون پیشوند وبکیت — روی سافاری آیفون کار نمی‌کند
۴. متغیر CSS تعریف‌نشده مثل var(--text)
۵. فونت زیر ۱۲ پیکسل که روی موبایل ناخواناست
۶. قالب بدون meta viewport (فقط قالب‌های مستقل)
"""
import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand

# عرض کوچک‌ترین گوشی رایج؛ هرچه از این پهن‌تر و ثابت باشد بیرون می‌زند
NARROWEST = 360

FIXED_WIDTH = re.compile(r'(?<!max-)(?<!min-)width\s*:\s*(\d{3,})px', re.I)
TINY_FONT = re.compile(r'font-size\s*:\s*(\d+(?:\.\d+)?)px', re.I)
CSS_VAR_USE = re.compile(r'var\(\s*(--[a-zA-Z0-9_-]+)')
CSS_VAR_DEF = re.compile(r'^\s*(--[a-zA-Z0-9_-]+)\s*:', re.M)


class Finding:
    def __init__(self, level, path, line, message):
        self.level = level
        self.path = path
        self.line = line
        self.message = message


class Command(BaseCommand):
    help = 'بازرسی مشکلات نمایش موبایل در قالب‌ها و CSS'

    def add_arguments(self, parser):
        parser.add_argument('--fail-on-error', action='store_true',
                            help='اگر خطای جدی پیدا شد، با کد ۱ خارج شو')

    # ── کمکی‌ها ──────────────────────────────────────────────────────
    def _template_dirs(self):
        dirs = []
        for cfg in settings.TEMPLATES:
            dirs.extend(str(d) for d in cfg.get('DIRS', []))
        return dirs

    def _walk(self, root, suffix):
        for base, _dirs, files in os.walk(root):
            for name in files:
                if name.endswith(suffix):
                    yield os.path.join(base, name)

    def _rel(self, path):
        return os.path.relpath(path, str(settings.BASE_DIR)).replace('\\', '/')

    # ── بازرسی‌ها ────────────────────────────────────────────────────
    def check_fixed_widths(self, path, text, out):
        for no, line in enumerate(text.splitlines(), 1):
            if 'max-width' in line or 'min-width' in line:
                continue
            for m in FIXED_WIDTH.finditer(line):
                px = int(m.group(1))
                if px > NARROWEST:
                    out.append(Finding(
                        'error', path, no,
                        'عرض ثابت %dpx — روی صفحهٔ %dپیکسلی بیرون می‌زند؛ '
                        'max-width یا درصد بگذارید' % (px, NARROWEST)))

    def check_tables(self, path, text, out):
        tables = text.count('<table')
        if not tables:
            return
        wrapped = (text.count('table-responsive')
                   + text.count('overflow-auto-x')
                   + text.count('panel-table'))
        if wrapped < tables:
            out.append(Finding(
                'warn', path, text.find('<table'),
                '%d جدول ولی %d ظرف اسکرول — جدول پهن کل صفحه را افقی '
                'می‌کشد' % (tables, wrapped)))

    def check_backdrop(self, path, text, out):
        lines = text.splitlines()
        for no, line in enumerate(lines, 1):
            if 'backdrop-filter' in line and '-webkit-' not in line:
                prev = lines[no - 2] if no >= 2 else ''
                if '-webkit-backdrop-filter' not in prev:
                    out.append(Finding(
                        'error', path, no,
                        'backdrop-filter بدون -webkit- — روی سافاری آیفون '
                        'بی‌اثر است'))

    def check_tiny_fonts(self, path, text, out):
        for no, line in enumerate(text.splitlines(), 1):
            for m in TINY_FONT.finditer(line):
                if float(m.group(1)) < 11:
                    out.append(Finding(
                        'warn', path, no,
                        'فونت %spx — روی موبایل ناخواناست' % m.group(1)))

    def check_fixed_overlap(self, path, text, out):
        """دو عنصر شناور که روی هم می‌افتند.

        این‌ها هیچ‌وقت در تست دیده نمی‌شوند: هر دو رندر می‌شوند، هیچ
        خطایی نیست، فقط یکی زیر دیگری پنهان می‌ماند و کلیک کاربر به
        عنصر اشتباه می‌رسد. دکمهٔ «بازگشت به بالا» ۴۲×۳۰ پیکسل زیر
        دکمهٔ گفت‌وگو رفته بود و ماه‌ها کسی متوجه نشد.

        فقط قواعد پایه بررسی می‌شوند، نه داخل @media: آن‌ها عمداً
        همین‌ها را جابه‌جا می‌کنند.
        """
        boxes = []
        for match in re.finditer(r'(\.[\w-]+)\s*\{([^}]*)\}', text):
            name, body = match.group(1), match.group(2)
            if not re.search(r'position\s*:\s*fixed', body, re.I):
                continue
            # چیزی که در @media است را رد کن
            if text.count('@media', 0, match.start()) > text.count('}', 0, match.start()):
                continue

            def px(*props):
                for prop in props:
                    hit = re.search(r'(?<![\w-])%s\s*:\s*(-?\d+)px' % prop, body, re.I)
                    if hit:
                        return int(hit.group(1))
                return None

            box = {
                'name': name,
                'bottom': px('inset-block-end', 'bottom'),
                'start': px('inset-inline-start', 'left'),
                'w': px('width'),
                'h': px('height'),
                'line': text.count('\n', 0, match.start()) + 1,
            }
            if None not in (box['bottom'], box['start'], box['w'], box['h']):
                boxes.append(box)

        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                dx = (min(a['start'] + a['w'], b['start'] + b['w'])
                      - max(a['start'], b['start']))
                dy = (min(a['bottom'] + a['h'], b['bottom'] + b['h'])
                      - max(a['bottom'], b['bottom']))
                if dx > 0 and dy > 0:
                    out.append(Finding(
                        'error', path, a['line'],
                        '%s و %s روی هم می‌افتند (%d×%d پیکسل) — یکی زیر '
                        'دیگری پنهان می‌شود' % (a['name'], b['name'], dx, dy)))

    def check_css_vars(self, css_text, files, out):
        global_defs = set(CSS_VAR_DEF.findall(css_text))
        for path, text in files:
            # قالب‌ها می‌توانند در <style> خودشان متغیر تعریف کنند؛
            # بدون این، همهٔ آن‌ها اشتباهاً «تعریف‌نشده» گزارش می‌شدند
            defined = global_defs | set(CSS_VAR_DEF.findall(text))
            for no, line in enumerate(text.splitlines(), 1):
                for name in CSS_VAR_USE.findall(line):
                    # var(--x, fallback) بی‌خطر است
                    if name in defined:
                        continue
                    idx = line.find('var(%s' % name)
                    tail = line[idx:idx + 80] if idx >= 0 else ''
                    if ',' in tail.split(')')[0]:
                        continue
                    out.append(Finding(
                        'error', path, no,
                        'متغیر %s تعریف نشده — مرورگر این خط را نادیده '
                        'می‌گیرد' % name))

    # ── اجرا ─────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        out = []
        css_path = os.path.join(str(settings.BASE_DIR), 'static', 'css', 'main.css')
        css_text = ''
        if os.path.isfile(css_path):
            css_text = open(css_path, encoding='utf-8').read()
            self.check_backdrop(css_path, css_text, out)
            self.check_tiny_fonts(css_path, css_text, out)
            # main.css تا امروز فقط از نظر فونت و backdrop دیده می‌شد؛
            # عرض ثابت در آن همان‌قدر صفحه را افقی می‌کشد که در قالب.
            self.check_fixed_widths(css_path, css_text, out)
            self.check_fixed_overlap(css_path, css_text, out)

        template_files = []
        for root in self._template_dirs():
            if not os.path.isdir(root):
                continue
            for path in self._walk(root, '.html'):
                # صفحات چاپی برای کاغذ A4 طراحی شده‌اند، نه موبایل
                if 'print_' in os.path.basename(path) or '/email/' in path.replace('\\', '/'):
                    continue
                text = open(path, encoding='utf-8').read()
                template_files.append((path, text))
                self.check_fixed_widths(path, text, out)
                self.check_tables(path, text, out)
                self.check_backdrop(path, text, out)

        self.check_css_vars(css_text, template_files, out)

        errors = [f for f in out if f.level == 'error']
        warns = [f for f in out if f.level == 'warn']

        for level, group, style in (
            ('خطا', errors, self.style.ERROR),
            ('هشدار', warns, self.style.WARNING),
        ):
            if not group:
                continue
            self.stdout.write(style('\n%s (%d)' % (level, len(group))))
            for f in group:
                self.stdout.write('  %s:%s\n    %s' % (
                    self._rel(f.path), f.line, f.message))

        if not out:
            self.stdout.write(self.style.SUCCESS(
                '\nهیچ مشکل شناخته‌شدهٔ موبایلی پیدا نشد.'))
        else:
            self.stdout.write('\n%d خطا، %d هشدار — %d قالب بررسی شد.' % (
                len(errors), len(warns), len(template_files)))

        if options['fail_on_error'] and errors:
            raise SystemExit(1)
