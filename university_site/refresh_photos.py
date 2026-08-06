#!/usr/bin/env python3
"""جایگزینی عکس افراد با نسخهٔ سند — یک‌بار مصرف.

چرا جدا از setup_directory.py
─────────────────────────────
`seed_directory` عمداً عکسی را که از قبل هست بازنویسی نمی‌کند، وگرنه
هر بار که اجرا شود عکسی که مدیر سایت دستی آپلود کرده از بین می‌رفت.
ولی وقتی سند تازه‌ای با عکس‌های بهتر می‌رسد، دقیقاً همان بازنویسی
لازم است.

اگر این را به `setup_directory.py` اضافه می‌کردم، هر دیپلوی عکس‌های
دستی را پاک می‌کرد. پس یک فایل جدا شد که فقط وقتی لازم است اجرا شود.

طرز استفاده
───────────
cPanel ← Setup Python App ← «Execute python script»:

    /home/cp29524/apps/university_site/refresh_photos.py

⚠️ هر عکسی که خودتان در پنل ادمین آپلود کرده باشید با نسخهٔ سند
جایگزین می‌شود. اگر عکس بهتری گذاشته‌اید، این را اجرا نکنید و
به‌جایش setup_directory.py معمولی را بزنید.
"""
from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))


def log(msg: str = '') -> None:
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
    except Exception as exc:              # noqa: BLE001 — پیام باید کامل دیده شود
        log('!! جنگو بالا نیامد: %s' % exc)
        log('   احتمالاً deploy.py هنوز اجرا نشده است.')
        return 1

    log('=' * 60)
    log('جایگزینی عکس‌ها با نسخهٔ سند')
    log('=' * 60)
    log('عکس‌های قبلی — از جمله هر عکسی که دستی آپلود شده — با')
    log('نسخهٔ داخل سند جایگزین می‌شوند.')
    log('')

    try:
        call_command('seed_directory', '--refresh-photos')
    except Exception as exc:              # noqa: BLE001
        log('!! شکست خورد: %s' % exc)
        return 1

    # گزارش وضعیت، چون بدون ترمینال راه دیگری برای دیدنش نیست
    log('')
    log('=' * 60)
    log('وضعیت تصویرهای سایت')
    log('=' * 60)
    try:
        call_command('photo_audit')
    except Exception as exc:              # noqa: BLE001
        log('(گزارش گرفته نشد: %s)' % exc)

    log('')
    log('=' * 60)
    log('پایان: موفق')
    log('=' * 60)
    log('حالا این صفحه‌ها را باز کنید:')
    log('  https://portal.aab.ac.ir/ریاست/')
    log('  https://portal.aab.ac.ir/دفترچه-تلفن/')
    log('  https://portal.aab.ac.ir/اعضای-موسسه/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
