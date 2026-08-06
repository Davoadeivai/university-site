"""ذخیره‌سازی فایل با نام ASCII.

مشکلی که این فایل حل می‌کند
────────────────────────────
آپلود هر فایلی که نامش فارسی باشد روی سرور خطای ۵۰۰ می‌داد:

    File "django/core/files/storage/filesystem.py", line 137, in _save
        fd = os.open(full_path, open_flags, 0o666)
    UnicodeEncodeError: 'ascii' codec can't encode characters ...

`os.open` مسیر را با `sys.getfilesystemencoding()` رمزگذاری می‌کند.
روی این هاست، پروسهٔ Passenger هیچ locale ندارد (`LANG` تنظیم نشده)،
پس پایتون به ASCII برمی‌گردد و هر حرف فارسی در نام فایل کار را
می‌شکند. چون کاربر فارسی‌زبان است، نام فایل‌هایش هم طبیعتاً فارسی
است — یعنی عملاً هیچ عکسی قابل آپلود نبود.

می‌شد به‌جای این، `PYTHONUTF8=1` را در تنظیمات اپ گذاشت. آن هم لازم
است، ولی کافی نیست: هر بار که اپ روی هاست دیگری برود یا کسی آن متغیر
را پاک کند، مشکل برمی‌گردد. نام ASCII در سطح کد، مستقل از محیط است —
و برای نشانی‌های اینترنتی هم پایدارتر است.

نام اصلی فایل از دست نمی‌رود در جایی که مهم است: مثلاً
`CurriculumDocument` عنوان فارسی را در دیتابیس نگه می‌دارد و هنگام
دانلود همان را به کاربر می‌دهد.
"""
from __future__ import annotations

import os
import re
import unicodedata
import uuid

from django.core.files.storage import FileSystemStorage

# فقط این‌ها در نام فایل می‌مانند
_SAFE = re.compile(r'[^A-Za-z0-9._-]+')
_TRIM = re.compile(r'[-_.]{2,}')

MAX_STEM = 60


def ascii_filename(name: str) -> str:
    """نام فایل را به شکلی برمی‌گرداند که روی هر فایل‌سیستمی بنشیند.

    حروف لاتینِ نزدیک نگه داشته می‌شوند (é → e)، بقیه حذف می‌شوند.
    اگر چیزی باقی نماند — که برای نام کاملاً فارسی همین‌طور است —
    یک شناسهٔ تصادفی می‌نشیند، چون نام خالی از نام غلط بدتر است.
    """
    stem, ext = os.path.splitext(name)

    # پسوند باید ASCII و کوتاه بماند؛ «.PNG» هم به «.png»
    ext = _SAFE.sub('', ext).lower()[:10]

    # NFKD حروف لاتین مزین را به پایه + علامت می‌شکند، بعد علامت‌ها
    # با encode('ascii', 'ignore') می‌افتند. حروف فارسی معادل لاتین
    # ندارند و کلاً حذف می‌شوند.
    folded = unicodedata.normalize('NFKD', stem)
    folded = folded.encode('ascii', 'ignore').decode('ascii')

    cleaned = _SAFE.sub('-', folded)
    cleaned = _TRIM.sub('-', cleaned).strip('-_.')

    if not cleaned:
        cleaned = 'file-%s' % uuid.uuid4().hex[:10]

    return cleaned[:MAX_STEM] + ext


class ASCIINameStorage(FileSystemStorage):
    """FileSystemStorage که نام هر فایل آپلودی را ASCII می‌کند."""

    def get_valid_name(self, name: str) -> str:
        return ascii_filename(name)

    def generate_filename(self, filename: str) -> str:
        """پوشه‌های `upload_to` را هم پاک‌سازی می‌کند.

        امروز همهٔ `upload_to`های پروژه ASCII هستند، ولی یکی که فارسی
        اضافه شود همان خطا را برمی‌گرداند و ردیابی‌اش سخت است.
        """
        filename = str(filename).replace('\\', '/')
        dirname, basename = os.path.split(filename)
        if dirname:
            parts = [
                _SAFE.sub('-', unicodedata.normalize('NFKD', part)
                          .encode('ascii', 'ignore').decode('ascii')).strip('-')
                or 'x'
                for part in dirname.split('/') if part not in ('', '.', '..')
            ]
            dirname = '/'.join(parts)
        return super().generate_filename(
            '%s/%s' % (dirname, basename) if dirname else basename)
