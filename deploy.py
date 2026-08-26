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

چه کاری انجام می‌دهد
────────────────────
کد را سر جایش می‌گذارد، migrate و collectstatic می‌زند، محتوای سند
رسمی را بارگذاری می‌کند (افراد، هیات‌ها، اساتید، سرفصل‌ها) و اپ را
ری‌استارت می‌کند. یک اجرا، همه‌چیز — دیگر لازم نیست اسکریپت دومی
پشت سرش زده شود.

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


def _ensure_dir(path: str) -> bool:
    """ساخت پوشه، با یک تلاش برای باز کردن مجوز پوشهٔ والد.

    روی سرور بعضی پوشه‌ها (مثلاً locale/fa) مجوز نوشتن ندارند و
    makedirs با PermissionError می‌افتاد و کل دیپلوی را متوقف می‌کرد.
    """
    if os.path.isdir(path):
        return True
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except PermissionError:
        pass
    parent = os.path.dirname(path)
    try:
        os.chmod(parent, 0o755)
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False


def _copy_file(src: str, dst: str) -> bool:
    """کپی با بازنویسی؛ اگر مقصد فقط‌خواندنی بود مجوزش باز می‌شود."""
    try:
        shutil.copyfile(src, dst)
        return True
    except PermissionError:
        pass
    try:
        if os.path.exists(dst):
            os.chmod(dst, 0o644)
        else:
            os.chmod(os.path.dirname(dst), 0o755)
        shutil.copyfile(src, dst)
        return True
    except OSError:
        return False


def copy_tree(src: str, dst: str, skipped: list) -> int:
    """کپی بازگشتی با بازنویسی. تعداد فایل‌های کپی‌شده را برمی‌گرداند.

    هرچه قابل کپی نباشد در `skipped` ثبت می‌شود و کار متوقف نمی‌شود —
    یک پوشهٔ ترجمهٔ بدون مجوز نباید جلوی رسیدن کد و CSS را بگیرد.
    """
    count = 0
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        parts = set(rel.split(os.sep))

        # وارد پوشه‌های محافظت‌شده نشو
        dirs[:] = [d for d in dirs if d not in KEEP]
        if parts & KEEP:
            continue

        dest_dir = dst if rel == '.' else os.path.join(dst, rel)
        if not _ensure_dir(dest_dir):
            skipped.append(rel + os.sep)
            dirs[:] = []          # وارد زیرشاخه‌هایش هم نشو
            continue

        for name in files:
            if name in KEEP or name.endswith('.pyc'):
                continue
            if _copy_file(os.path.join(root, name), os.path.join(dest_dir, name)):
                count += 1
            else:
                skipped.append(os.path.join(rel, name) if rel != '.' else name)
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


def check_media() -> None:
    """پوشهٔ آپلود را می‌سازد و واقعاً در آن می‌نویسد.

    `public/media` را هیچ‌کس نمی‌ساخت: این اسکریپت پوشهٔ public را
    در KEEP دارد و دست نمی‌زند، و collectstatic فقط STATIC_ROOT را
    می‌سازد. نتیجه‌اش خطای ۵۰۰ هنگام آپلود عکس در پنل ادمین بود، که
    هیچ ربطی به آن صفحه نداشت.

    os.access روی بعضی هاست‌ها دروغ می‌گوید، پس واقعاً یک فایل
    نوشته و پاک می‌شود.
    """
    media = os.path.join(TARGET, 'public', 'media')
    log('\nپوشهٔ آپلود: %s' % media)
    try:
        os.makedirs(media, exist_ok=True)
    except OSError as exc:
        log('!! ساخته نشد: %s' % exc)
        log('   آپلود عکس در پنل ادمین خطای ۵۰۰ می‌دهد.')
        return

    probe = os.path.join(media, '.write-probe')
    try:
        with open(probe, 'w') as fh:
            fh.write('ok')
        os.remove(probe)
        log('  نوشتن آزمایشی موفق بود.')
    except OSError as exc:
        log('!! نوشتن ممکن نیست: %s' % exc)
        log('   در File Manager مجوز این پوشه را روی 755 بگذارید.')


def seed_content() -> None:
    """بارگذاری محتوای سند رسمی — همان کاری که setup_directory.py می‌کرد.

    چرا اینجا و نه در یک اسکریپت جدا
    ────────────────────────────────
    ترتیب «Update from Remote ← deploy.py ← setup_directory.py» چهار
    بار پشت سر هم نصفه اجرا شد و هر بار نتیجه یکی بود: اسکریپت دوم
    روی کدِ کپی‌نشده اجرا می‌شد، بی‌خطا تمام می‌شد، و صفحه خالی
    می‌ماند. یک مرحلهٔ کمتر یعنی یک جای کمتر برای اشتباه.

    هر سه دستور عمداً بی‌خطرند اگر بارها اجرا شوند: ردیف تکراری
    نمی‌سازند، و متن یا عکسی را که ادمین وارد کرده بازنویسی نمی‌کنند —
    فقط جاهای خالی را پر می‌کنند. پس اجرای‌شان در هر دیپلوی مشکلی
    نمی‌سازد.

    شکست هرکدام گزارش می‌شود ولی جلوی بقیه را نمی‌گیرد؛ نرسیدن
    سرفصل‌ها نباید مانع ساخته‌شدن اساتید شود.
    """
    log('\n' + '=' * 60)
    log('بارگذاری محتوا')
    log('=' * 60)

    run('fix_academic_years')
    # --trust-document: موسسه تأیید کرد که سند ۱۴۰۴ مرجع نام معاونان است
    run('seed_directory', '--trust-document')
    run('import_from_directory')
    # سه رشته‌ای که در سند وزارت هستند و موسسه تأیید کرد دایرند
    run('import_major_codes', '--create', '8381,7129,7180',
        '--activate', '8381,7129,7180')
    run('import_term_plans')
    run('tidy_academic_structure')
    run('set_org_chart')
    run('set_contact_email', '--replace')
    run('set_president_links')
    # سه دانشکده و چیدن گروه‌ها و رشته‌ها زیرشان
    run('set_faculties')
    run('seed_president_cv')
    run('prefix_doctor_titles')
    run('set_graduate_groups')

    incoming = os.path.join(TARGET, 'media', '_incoming')
    if os.path.isdir(incoming):
        manifest = os.path.join(incoming, 'manifest.json')
        args = ['import_curricula', '--source', incoming, '--move']
        if os.path.isfile(manifest):
            args += ['--manifest', manifest]
        run(*args)
    else:
        log('\nپوشهٔ media/_incoming نیست — وارد کردن سرفصل‌ها رد شد.')


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

    skipped: list = []
    n = copy_tree(SOURCE, TARGET, skipped)
    log('\n%d فایل کپی شد.' % n)
    if skipped:
        log('\n%d مورد به‌خاطر نداشتن مجوز رد شد:' % len(skipped))
        for item in skipped[:30]:
            log('  - %s' % item)
        if len(skipped) > 30:
            log('  … و %d مورد دیگر' % (len(skipped) - 30))
        log('اگر بین این‌ها فایل کد یا CSS نبود، مشکلی نیست.')

    # migrate پیش از collectstatic — اگر ساختار دیتابیس عقب باشد،
    # دستورهای بعدی هم می‌شکنند.
    ok = run('migrate', '--noinput')

    # جدول کش — فقط وقتی CACHE_BACKEND=database است معنا دارد. اگر از
    # قبل ساخته شده باشد پیام می‌دهد و رد می‌شود، پس هر بار بی‌خطر است.
    if ok:
        run('createcachetable')

    if ok:
        ok = run('collectstatic', '--noinput')

    check_media()

    if ok:
        seed_content()

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
