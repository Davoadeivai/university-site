#!/usr/bin/env python3
"""دانلود و وارد کردن سرفصل‌ها — بدون کار با File Manager.

چرا این فایل هست
────────────────
راه قبلی یعنی آپلود ۹ فایل zip از طریق File Manager، استخراج تک‌تک،
و پاک کردن دستی‌شان. هر مرحله‌اش جای خطا داشت و آپلود ۵۰ مگابایتی از
مرورگر روی خط ایران نصفه می‌ماند.

این اسکریپت همان کار را از سمت سرور انجام می‌دهد: آرشیو را از یک
نشانی اینترنتی می‌گیرد، PDFها را یکی‌یکی سر جایشان می‌گذارد و آرشیو
را پاک می‌کند. آپلود از سمت شما فقط یک بار به دراپ‌باکس است.

طرز استفاده
───────────
۱. نشانی دانلود مستقیم آرشیو را در این فایل بگذارید:

       /home/cp29524/apps/university_site/media/curricula_url.txt

   یک خط، فقط نشانی. برای دراپ‌باکس آخر لینک باید `dl=1` باشد نه
   `dl=0` — اگر `dl=0` بگذارید خود اسکریپت اصلاحش می‌کند.

۲. cPanel ← Setup Python App ← «Execute python script»:

       /home/cp29524/apps/university_site/fetch_curricula.py

اجرای دوباره‌اش بی‌خطر است: رکوردها با کلید (مقطع، عنوان، تاریخ)
به‌روز می‌شوند، نه اینکه تکراری ساخته شود.
"""
from __future__ import annotations

import os
import shutil
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
URL_FILE = os.path.join(BASE, 'media', 'curricula_url.txt')
TMP_ZIP = os.path.join(BASE, 'media', '_curricula_download.zip')

# دانلود ~۳۰۰ مگابایتی روی هاست اشتراکی نباید دیسک را پر کند.
MIN_FREE_MB = 700


def log(msg: str) -> None:
    print(msg)
    sys.stdout.flush()


def read_url() -> str:
    if not os.path.isfile(URL_FILE):
        log('!! فایل نشانی پیدا نشد: %s' % URL_FILE)
        log('   یک فایل متنی با همین نام بسازید و لینک دانلود را در آن بگذارید.')
        return ''
    with open(URL_FILE, encoding='utf-8') as fh:
        url = fh.read().strip()
    if not url:
        log('!! فایل نشانی خالی است.')
        return ''
    # دراپ‌باکس با dl=0 صفحهٔ HTML می‌دهد نه خود فایل
    if 'dropbox.com' in url:
        url = url.replace('?dl=0', '?dl=1').replace('&dl=0', '&dl=1')
        if 'dl=' not in url:
            url += ('&' if '?' in url else '?') + 'dl=1'
    return url


def enough_disk() -> bool:
    try:
        free_mb = shutil.disk_usage(BASE).free / 1048576
    except OSError:
        return True                      # نتوانستیم بسنجیم؛ جلوی کار را نگیریم
    log('فضای آزاد: %.0f مگابایت' % free_mb)
    if free_mb < MIN_FREE_MB:
        log('!! کمتر از %d مگابایت آزاد است. اول فضا خالی کنید.' % MIN_FREE_MB)
        log('   فایل backup-*.tar.gz در پوشهٔ خانه معمولاً بزرگ‌ترین است.')
        return False
    return True


def download(url: str) -> bool:
    log('دانلود از: %s' % url[:90])
    os.makedirs(os.path.dirname(TMP_ZIP), exist_ok=True)

    request = urllib.request.Request(
        url, headers={'User-Agent': 'Mozilla/5.0 (curricula-fetch)'})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            total = int(response.headers.get('Content-Length') or 0)
            if total:
                log('حجم: %.1f مگابایت' % (total / 1048576))
            done = 0
            step = 0
            with open(TMP_ZIP, 'wb') as out:
                while True:
                    chunk = response.read(1024 * 512)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    # هر ۲۵ مگابایت یک خط، تا لاگ سنگین نشود
                    if done // (25 * 1048576) > step:
                        step = done // (25 * 1048576)
                        log('  … %.0f مگابایت' % (done / 1048576))
    except Exception as exc:              # noqa: BLE001 — متن خطا باید دیده شود
        log('!! دانلود شکست خورد: %s' % exc)
        return False

    size_mb = os.path.getsize(TMP_ZIP) / 1048576
    log('دانلود تمام شد: %.1f مگابایت' % size_mb)

    # دراپ‌باکس وقتی لینک اشتباه باشد یک صفحهٔ HTML کوچک می‌دهد
    with open(TMP_ZIP, 'rb') as fh:
        if fh.read(2) != b'PK':
            log('!! فایل دانلودشده zip نیست — احتمالاً لینک، صفحهٔ دراپ‌باکس')
            log('   است نه فایل. مطمئن شوید آخر لینک dl=1 باشد.')
            return False
    return True


def main() -> int:
    os.chdir(BASE)
    sys.path.insert(0, BASE)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_prod')

    url = read_url()
    if not url:
        return 1
    if not enough_disk():
        return 1
    if not download(url):
        return 1

    try:
        import django
        django.setup()
        from django.core.management import call_command
    except Exception as exc:              # noqa: BLE001
        log('!! جنگو بالا نیامد: %s' % exc)
        return 1

    log('')
    log('=' * 60)
    log('وارد کردن سرفصل‌ها')
    log('=' * 60)
    try:
        call_command('import_curricula', '--zip', TMP_ZIP)
    except Exception as exc:              # noqa: BLE001
        log('!! ایمپورت شکست خورد: %s' % exc)
        return 1
    finally:
        # آرشیو در هر حالت پاک می‌شود؛ ۳۰۰ مگابایت نباید روی هاست بماند
        if os.path.exists(TMP_ZIP):
            os.remove(TMP_ZIP)
            log('\nآرشیو موقت پاک شد.')

    log('')
    log('=' * 60)
    log('پایان: موفق')
    log('=' * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
