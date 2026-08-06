#!/usr/bin/env python3
"""گزارش وضعیت سرور — برای وقتی که چیزی کار نمی‌کند و دلیلش معلوم نیست.

    cPanel ← Setup Python App ← «Execute python script»:
        /home/cp29524/repositories/university-site/diagnose.py

هیچ چیزی را عوض نمی‌کند؛ فقط می‌خواند و گزارش می‌دهد. خروجی‌اش را
کامل کپی کنید.

مهم‌ترین بخشش «آخرین خطاها» در انتهاست: جنگو با DEBUG=False متن کامل
خطای ۵۰۰ را در logs/django.log می‌نویسد، و همان متن است که می‌گوید
مشکل کجاست — نه حدس.
"""
from __future__ import annotations

import os
import sys
import traceback

APP = os.environ.get('DIAGNOSE_APP', '/home/cp29524/apps/university_site')
REPO = os.path.dirname(os.path.abspath(__file__))


def log(msg: str = '') -> None:
    print(msg)
    sys.stdout.flush()


def head(title: str) -> None:
    log('')
    log('=' * 66)
    log('  ' + title)
    log('=' * 66)


def safe(label: str, fn) -> None:
    """هر بررسی جدا؛ شکست یکی نباید بقیهٔ گزارش را قطع کند."""
    try:
        value = fn()
    except Exception as exc:                       # noqa: BLE001
        value = '!! %s: %s' % (type(exc).__name__, exc)
    log('  %-28s %s' % (label + ':', value))


# ── ۱) کد ──────────────────────────────────────────────────────────────
def git_head(path: str) -> str:
    head_file = os.path.join(path, '.git', 'HEAD')
    if not os.path.isfile(head_file):
        return '(مخزن گیت نیست)'
    with open(head_file) as fh:
        ref = fh.read().strip()
    if ref.startswith('ref: '):
        ref_path = os.path.join(path, '.git', ref[5:])
        if os.path.isfile(ref_path):
            with open(ref_path) as fh:
                return fh.read().strip()[:7] + '  (' + ref[5:] + ')'
        return '(ref پیدا نشد) ' + ref
    return ref[:7]


def newest(path: str, names) -> str:
    import datetime
    out = []
    for name in names:
        full = os.path.join(path, name)
        if os.path.exists(full):
            when = datetime.datetime.fromtimestamp(os.path.getmtime(full))
            out.append('%s=%s' % (name, when.strftime('%m-%d %H:%M')))
        else:
            out.append('%s=نیست' % name)
    return '  '.join(out)


def main() -> int:
    head('۱) کد روی سرور')
    safe('مخزن', lambda: REPO)
    safe('کامیت مخزن', lambda: git_head(REPO))
    safe('پوشهٔ اپ', lambda: APP if os.path.isdir(APP) else '!! پیدا نشد: ' + APP)
    safe('فایل‌های کلیدی اپ', lambda: newest(APP, [
        'manage.py', 'setup_directory.py', 'fetch_curricula.py']))
    safe('اپ directory', lambda: 'هست' if os.path.isdir(
        os.path.join(APP, 'directory')) else '!! نیست — deploy.py اجرا نشده')
    safe('آخرین ری‌استارت', lambda: newest(APP, ['tmp/restart.txt']))

    if not os.path.isdir(APP):
        log('\n!! بدون پوشهٔ اپ ادامه ممکن نیست.')
        return 1

    os.chdir(APP)
    sys.path.insert(0, APP)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_prod')

    head('۲) تنظیمات')
    try:
        import django
        django.setup()
        from django.conf import settings
    except Exception:                              # noqa: BLE001
        log('!! جنگو بالا نیامد:')
        log(traceback.format_exc())
        return 1

    safe('نسخهٔ جنگو', lambda: django.get_version())
    safe('پایتون', lambda: sys.version.split()[0])
    safe('DEBUG', lambda: settings.DEBUG)
    safe('ALLOWED_HOSTS', lambda: settings.ALLOWED_HOSTS)
    safe('دیتابیس', lambda: settings.DATABASES['default']['ENGINE'].split('.')[-1])
    safe('CACHE', lambda: settings.CACHES['default']['BACKEND'].split('.')[-1])
    safe('STATIC_ROOT', lambda: settings.STATIC_ROOT)
    safe('MEDIA_ROOT', lambda: settings.MEDIA_ROOT)
    safe('directory نصب شده', lambda: any(
        'directory' in a for a in settings.INSTALLED_APPS))

    head('۳) پوشهٔ media — جای آپلود عکس')
    media = str(settings.MEDIA_ROOT)
    safe('وجود دارد', lambda: os.path.isdir(media))
    safe('اجازهٔ نوشتن', lambda: os.access(media, os.W_OK)
         if os.path.isdir(media) else '(پوشه نیست)')

    def write_test():
        """آزمون واقعی نوشتن — os.access روی بعضی هاست‌ها دروغ می‌گوید."""
        probe_dir = os.path.join(media, 'probe')
        probe = os.path.join(probe_dir, 'test.txt')
        try:
            os.makedirs(probe_dir, exist_ok=True)
            with open(probe, 'w') as fh:
                fh.write('ok')
            os.remove(probe)
            os.rmdir(probe_dir)
            return 'موفق — آپلود باید کار کند'
        except Exception as exc:                   # noqa: BLE001
            return '!! %s: %s   ← علت خطای ۵۰۰ در آپلود' % (
                type(exc).__name__, exc)

    safe('آزمون نوشتن', write_test)
    safe('والد media', lambda: '%s (نوشتن: %s)' % (
        os.path.dirname(media), os.access(os.path.dirname(media), os.W_OK)))
    safe('Pillow', lambda: __import__('PIL').__version__)

    head('۴) جدول‌ها و داده')
    from django.db import connection
    safe('جدول‌های directory', lambda: [
        t for t in connection.introspection.table_names()
        if t.startswith('directory_')] or '!! هیچ — migrate اجرا نشده')

    def counts():
        from directory.models import (
            CurriculumDocument, DirectoryPerson, ExternalResource)
        return 'افراد=%d  سرفصل=%d  منابع=%d' % (
            DirectoryPerson.objects.count(),
            CurriculumDocument.objects.count(),
            ExternalResource.objects.count())

    safe('تعداد رکوردها', counts)

    def core_counts():
        from core.models import BoardMember, PresidencyOffice, SecurityOffice
        return 'هیات=%d  دفتر ریاست=%d  حراست=%d' % (
            BoardMember.objects.count(),
            PresidencyOffice.objects.count(),
            SecurityOffice.objects.count())

    safe('رکوردهای core', core_counts)

    head('۵) نشانی‌های جدید')
    from django.urls import reverse
    for name in ('directory:staff', 'directory:people',
                 'directory:curricula', 'directory:resources'):
        safe(name, lambda n=name: reverse(n))

    head('۶) بازکردن صفحه‌های ادمینِ مشکل‌دار')
    log('  همان صفحه‌ها با کاربر ادمین باز می‌شوند تا اگر ۵۰۰ بدهند،')
    log('  متن کامل خطا همین‌جا چاپ شود. فقط خواندن است — GET، نه ذخیره.')
    log('')
    try:
        from django.contrib.auth import get_user_model
        from django.test import Client

        admin_user = get_user_model().objects.filter(
            is_superuser=True, is_active=True).first()
        if admin_user is None:
            log('  !! هیچ کاربر superuser فعالی نیست — این بررسی رد شد.')
        else:
            # تست‌کلاینت با نام میزبان testserver کار می‌کند
            if 'testserver' not in settings.ALLOWED_HOSTS:
                settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
            client = Client()
            client.force_login(admin_user)
            log('  کاربر: %s' % admin_user.get_username())

            from core.models import PresidencyOffice, SecurityOffice
            targets = [
                ('core_presidencyoffice', PresidencyOffice),
                ('core_securityoffice', SecurityOffice),
            ]
            for route, model in targets:
                obj = model.objects.first()
                if obj is None:
                    log('  %-24s (رکوردی وجود ندارد)' % route)
                    continue
                url = '/admin/core/%s/%d/change/' % (route.split('_')[1], obj.pk)
                try:
                    res = client.get(url)
                    log('  %-46s → %s' % (url, res.status_code))
                except Exception:                  # noqa: BLE001
                    log('  %-46s → ۵۰۰' % url)
                    log('  ── متن کامل خطا ' + '─' * 42)
                    for line in traceback.format_exc().splitlines():
                        log('  ' + line)
                    log('  ' + '─' * 58)
    except Exception:                              # noqa: BLE001
        log('  !! خود این بررسی خطا داد:')
        log(traceback.format_exc())

    head('۷) فایل‌های ثابت')
    static = str(settings.STATIC_ROOT)
    safe('پوشه هست', lambda: os.path.isdir(static))
    safe('main.css', lambda: newest(static, ['css/main.css']))

    head('۸) آخرین خطاها  ← مهم‌ترین بخش')
    log_file = os.path.join(APP, 'logs', 'django.log')
    if not os.path.isfile(log_file):
        log('  فایل لاگ وجود ندارد: %s' % log_file)
        log('  یعنی از زمان ساخته شدنش هیچ خطای ۵۰۰ ثبت نشده،')
        log('  یا پوشهٔ logs اجازهٔ نوشتن ندارد.')
    else:
        size = os.path.getsize(log_file)
        log('  %s  (%.0f کیلوبایت)' % (log_file, size / 1024))
        log('  ── ۸۰ خط آخر ' + '─' * 45)
        try:
            with open(log_file, encoding='utf-8', errors='replace') as fh:
                lines = fh.readlines()
            for line in lines[-80:]:
                log('  ' + line.rstrip())
        except Exception as exc:                   # noqa: BLE001
            log('  !! خواندن لاگ ممکن نشد: %s' % exc)

    log('')
    log('=' * 66)
    log('  پایان گزارش — همهٔ متن بالا را کپی کنید')
    log('=' * 66)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                              # noqa: BLE001
        log('!! خود گزارش‌گیر خطا داد:')
        log(traceback.format_exc())
        sys.exit(1)
