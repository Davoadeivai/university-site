"""کد را از پوشهٔ مخزن به پوشهٔ اپ می‌برد، بعد migrate و collectstatic.

وقتی دکمهٔ Deploy HEAD Commit کار نمی‌کند، همین اسکریپت جای آن را
می‌گیرد. در «Setup Python App ← Run Script» با نشانی کامل صدایش کنید:

  /home/cp29524/repositories/university-site/university_site/run_deploy.py

اسکریپت از پوشهٔ خودش می‌خواند و در پوشهٔ اپ می‌نویسد، پس اول باید
«Update from Remote» زده باشید تا مخزن تازه باشد.

  python run_deploy.py                 # کپی + migrate + collectstatic + ری‌استارت
  python run_deploy.py --copy-only     # فقط کپی، بی‌آنکه به دیتابیس دست بزند
  python run_deploy.py --to /path/app  # اگر پوشهٔ اپ جای دیگری است

فایل‌های خود سرور — env. و media و دیتابیس و استاتیک جمع‌شده — کپی
نمی‌شوند و دست‌نخورده می‌مانند. چیزی هم پاک نمی‌شود؛ فقط فایل‌های
تازه‌تر روی قدیمی می‌نشینند.
"""
import os
import shutil
import sys

SOURCE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGET = '/home/cp29524/apps/university_site'

# اینها مال سرور است، نه مال مخزن — دست نمی‌خورند
SKIP_DIRS = {
    '.git', '__pycache__', 'media', 'public', 'staticfiles',
    'logs', 'tmp', '.venv', 'venv', 'node_modules',
}
SKIP_FILES = {'.env', 'db.sqlite3'}


def _target_from_argv(argv):
    if '--to' in argv:
        return argv[argv.index('--to') + 1]
    return os.environ.get('APP_DIR', DEFAULT_TARGET)


def copy_tree(source, target):
    """فایل‌های تازه‌تر مخزن را روی پوشهٔ اپ می‌نویسد."""
    copied = 0
    for folder, dirnames, filenames in os.walk(source):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        relative = os.path.relpath(folder, source)
        destination = target if relative == '.' else os.path.join(target, relative)
        os.makedirs(destination, exist_ok=True)
        for name in filenames:
            if name in SKIP_FILES or name.endswith('.pyc'):
                continue
            src_file = os.path.join(folder, name)
            dst_file = os.path.join(destination, name)
            if os.path.exists(dst_file):
                same_size = os.path.getsize(src_file) == os.path.getsize(dst_file)
                fresh = os.path.getmtime(src_file) <= os.path.getmtime(dst_file)
                if same_size and fresh:
                    continue
            shutil.copy2(src_file, dst_file)
            copied += 1
    return copied


def drop_stale_bytecode(target):
    """__pycache__ کهنه گاهی کد قدیمی را زنده نگه می‌دارد."""
    removed = 0
    for folder, dirnames, _ in os.walk(target):
        if '__pycache__' in dirnames:
            shutil.rmtree(os.path.join(folder, '__pycache__'), ignore_errors=True)
            dirnames.remove('__pycache__')
            removed += 1
    return removed


def main(argv):
    target = _target_from_argv(argv)
    if os.path.abspath(target) == SOURCE:
        print('پوشهٔ مبدأ و مقصد یکی است؛ کاری لازم نیست.')
        return 0
    if not os.path.isdir(target):
        print('پوشهٔ اپ پیدا نشد: %s' % target)
        print('با \u200E--to نشانی درست را بدهید.')
        return 1

    print('=== کپی از %s' % SOURCE)
    print('===      به %s' % target)
    print('  %d فایل تازه شد' % copy_tree(SOURCE, target))
    print('  %d پوشهٔ __pycache__ پاک شد' % drop_stale_bytecode(target))

    if '--copy-only' in argv:
        print('=== فقط کپی خواسته شده بود؛ همین‌جا تمام. ===')
        return 0

    sys.path.insert(0, target)
    os.chdir(target)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_prod')

    import django
    django.setup()
    from django.core.management import call_command

    print('=== migrate ===')
    call_command('migrate', '--noinput')
    print('=== collectstatic ===')
    call_command('collectstatic', '--noinput')

    import pathlib
    pathlib.Path(target, 'tmp').mkdir(exist_ok=True)
    pathlib.Path(target, 'tmp', 'restart.txt').touch()
    print('=== restart.txt لمس شد — سایت ری‌استارت می‌شود ===')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
