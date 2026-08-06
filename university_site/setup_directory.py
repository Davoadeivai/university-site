#!/usr/bin/env python3
"""بارگذاری «بانک اطلاعات موسسه» — یک‌بار بعد از دیپلوی.

چرا این فایل هست
────────────────
روی این هاست «Execute python script» فقط یک فایل .py را اجرا می‌کند و
دستور شل نمی‌پذیرد، پس `manage.py seed_directory` را نمی‌شود مستقیم
صدا زد. این اسکریپت همان کار را می‌کند.

طرز استفاده
───────────
cPanel ← Setup Python App ← اپ ← بخش «Execute python script»:

    /home/cp29524/apps/university_site/setup_directory.py

پیش از آن deploy.py را اجرا کنید تا جدول‌ها ساخته شوند.

چه کار می‌کند
─────────────
۱. seed_directory — افراد، هیات‌ها، عکس‌ها و منابع بیرونی
۲. import_curricula — فقط اگر پوشهٔ media/_incoming وجود داشته باشد

هر دو بی‌خطرند اگر چند بار اجرا شوند: ردیف تکراری ساخته نمی‌شود و
عکسی که در ادمین آپلود شده بازنویسی نمی‌شود.

هشدار دربارهٔ اجرای مکرر
────────────────────────
seed_directory سمت و شماره داخلی را از فایل JSON بازنویسی می‌کند. اگر
این مقادیر را در پنل ادمین دستی عوض کرده‌اید، اجرای دوباره آن‌ها را به
حالت سند برمی‌گرداند. پس این را فقط وقتی اجرا کنید که سند رسمی موسسه
عوض شده باشد.
"""
from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
INCOMING = os.path.join(BASE, 'media', '_incoming')
MANIFEST = os.path.join(INCOMING, 'manifest.json')


def log(msg: str) -> None:
    print(msg)
    sys.stdout.flush()


def main() -> int:
    os.chdir(BASE)
    sys.path.insert(0, BASE)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_prod')

    try:
        import django
        django.setup()
        from django.core.management import call_command
    except Exception as exc:            # noqa: BLE001 — پیام باید کامل دیده شود
        log('!! جنگو بالا نیامد: %s' % exc)
        log('   احتمالاً deploy.py هنوز اجرا نشده یا .env ناقص است.')
        return 1

    log('=' * 60)
    log('۱) بارگذاری افراد، هیات‌ها و منابع')
    log('=' * 60)
    try:
        call_command('seed_directory')
    except Exception as exc:            # noqa: BLE001
        log('!! seed_directory شکست خورد: %s' % exc)
        return 1

    log('')
    log('=' * 60)
    log('۲) وارد کردن سرفصل‌های مصوب')
    log('=' * 60)

    if not os.path.isdir(INCOMING):
        log('پوشهٔ %s وجود ندارد — این مرحله رد شد.' % INCOMING)
        log('اگر سرفصل‌ها را آپلود کرده‌اید، مسیر را بررسی کنید.')
        return 0

    args = ['--source', INCOMING, '--move']
    if os.path.isfile(MANIFEST):
        args += ['--manifest', MANIFEST]
    else:
        log('manifest.json پیدا نشد — عنوان‌ها از نام فایل حدس زده می‌شوند.')

    try:
        call_command('import_curricula', *args)
    except Exception as exc:            # noqa: BLE001
        log('!! import_curricula شکست خورد: %s' % exc)
        return 1

    log('')
    log('=' * 60)
    log('پایان: موفق')
    log('=' * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
