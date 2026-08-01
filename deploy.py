#!/usr/bin/env python3
"""دیپلوی دستی — بدون نیاز به ترمینال و بدون صف دیپلوی cPanel.

چرا این فایل هست
────────────────
`.cpanel.yml` وقتی کار می‌کند که صف دیپلوی cPanel روی سرور فعال باشد.
روی این هاست دکمهٔ «Deploy HEAD Commit» هیچ اجرایی ثبت نمی‌کند، پس
همان کارها اینجا با پایتون خالص انجام می‌شود.

طرز استفاده
───────────
cPanel ← Setup Python App ← اپ ← بخش «Execute python script»:

    /home/cp29524/repositories/university-site/deploy.py

پیش از آن یک بار «Update from Remote» را در صفحهٔ گیت بزنید تا آخرین
کد روی سرور بیاید. این اسکریپت فقط همان کد را سر جایش می‌گذارد.

چه چیزهایی دست‌نخورده می‌مانند
──────────────────────────────
.env، media/، logs/، دیتابیس، و خروجی collectstatic. یعنی هیچ دادهٔ
زنده‌ای با دیپلوی از بین نمی‌رود.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

# ── تنظیمات ────────────────────────────────────────────────────────
SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'university_site')
TARGET = '/home/cp29524/apps/university_site'

# این‌ها هرگز از مبدأ کپی نمی‌شوند و در مقصد هم پاک نمی‌شوند
KEEP = {
    '.env', 'media', 'logs', 'db.sqlite3',
    'public', 'staticfiles', 'tmp', '__pycache__', '.git',
}


def log(msg: str) -> None:
    print(msg)
    sys.stdout.flush()


def copy_tree(src: str, dst: str) -> int:
    """کپی بازگشتی با بازنویسی. تعداد فایل‌های کپی‌شده را برمی‌گرداند."""
    count = 0
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        parts = set(rel.split(os.sep))

        # وارد پوشه‌های محافظت‌شده نشو
        dirs[:] = [d for d in dirs if d not in KEEP]
        if parts & KEEP:
            continue

        dest_dir = dst if rel == '.' else os.path.join(dst, rel)
        os.makedirs(dest_dir, exist_ok=True)

        for name in files:
            if name in KEEP or name.endswith('.pyc'):
                continue
            shutil.copy2(os.path.join(root, name), os.path.join(dest_dir, name))
            count += 1
    return count


def run(*args: str) -> bool:
    """اجرای manage.py با همان پایتونی که این اسکریپت را اجرا کرده."""
    cmd = [sys.executable, os.path.join(TARGET, 'manage.py'), *args]
    log('\n$ manage.py %s' % ' '.join(args))
    result = subprocess.run(
        cmd, cwd=TARGET, capture_output=True, text=True, timeout=600,
    )
    out = (result.stdout or '').strip()
    err = (result.stderr or '').strip()
    if out:
        log(out[-4000:])
    if err:
        log('--- stderr ---')
        log(err[-4000:])
    if result.returncode != 0:
        log('!! این مرحله با کد %d شکست خورد' % result.returncode)
        return False
    return True


def main() -> int:
    log('=' * 60)
    log('مبدأ : %s' % SOURCE)
    log('مقصد : %s' % TARGET)
    log('=' * 60)

    if not os.path.isdir(SOURCE):
        log('!! پوشهٔ مبدأ پیدا نشد. اول «Update from Remote» را بزنید.')
        return 1
    if not os.path.isdir(TARGET):
        log('!! پوشهٔ مقصد پیدا نشد: %s' % TARGET)
        return 1

    n = copy_tree(SOURCE, TARGET)
    log('\n%d فایل کپی شد.' % n)

    # migrate پیش از collectstatic — اگر ساختار دیتابیس عقب باشد،
    # دستورهای بعدی هم می‌شکنند.
    ok = run('migrate', '--noinput')
    if ok:
        ok = run('collectstatic', '--noinput')

    # ری‌استارت: Passenger این فایل را می‌بیند و worker را تازه می‌کند
    tmp_dir = os.path.join(TARGET, 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    with open(os.path.join(tmp_dir, 'restart.txt'), 'w') as fh:
        fh.write('')
    log('\nاپلیکیشن ری‌استارت شد (tmp/restart.txt).')

    log('\n' + '=' * 60)
    log('پایان: %s' % ('موفق' if ok else 'با خطا — متن بالا را بفرستید'))
    log('=' * 60)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
