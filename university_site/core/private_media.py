"""پرونده‌های خصوصی، پشت در بسته.

مشکل
────
هر چیزی که کاربر آپلود می‌کرد زیر \u200E/media/\u200E می‌نشست و آپاچی مستقیم
تحویلش می‌داد — بی‌آنکه کسی بپرسد شما کی هستید. یعنی تصویر کارت ملی
یک داوطلب، فیش واریزی یک دانشجو، یا مدرک تخفیف شهریه، با دانستن
نشانی برای هر کسی در اینترنت باز می‌شد. نشانی هم حدس‌زدنی بود: نام
فایلِ آپلودشده همان نامی می‌ماند که کاربر داده بود، و \u200Ephoto.jpg\u200E و
\u200EIMG_1234.jpg\u200E را می‌شود حدس زد.

راه‌حل
──────
پوشه‌های حساس از دست آپاچی درمی‌آیند و از همین‌جا سرو می‌شوند، بعد
از اینکه پرسیدیم درخواست‌کننده کیست:

* کارمند و مدیر: همه را می‌بیند — کارشان همین است.
* دانشجو: فقط پرونده‌ای را که خودش فرستاده.
* مهمان: هیچ.

و از این به بعد نام فایل‌ها تصادفی است، پس حتی اگر روزی قاعده‌ای در
وب‌سرور از قلم بیفتد، نشانی حدس زده نمی‌شود.

نکتهٔ کارگذاری
──────────────
\u200E.htaccess\u200E باید این پیشوندها را به جنگو بسپارد، نه به پوشهٔ
\u200Epublic/media\u200E. قاعده‌اش آنجا نوشته شده و تستِ \u200Etests_private_media\u200E
نگهبانش است.
"""
from __future__ import annotations

import posixpath
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousFileOperation
from django.http import FileResponse, Http404
from django.utils.deconstruct import deconstructible

# پوشه‌هایی که هیچ‌وقت نباید مستقیم از وب‌سرور بیرون بروند.
#
# هر کدام دستِ کم یکی از این‌هاست: مدرک هویتی، سند مالی، یا نوشتهٔ
# خصوصی میان دانشجو و موسسه.
PRIVATE_PREFIXES = (
    'admissions/docs/',      # کارت ملی، مدرک پیشین، عکس، کارت پایان خدمت
    'payments/',             # فیش واریزی داوطلب
    'tuition_receipts/',     # فیش شهریه دانشجو
    'tuition_discounts/',    # مدرک تخفیف — اغلب سند پزشکی یا مالی خانواده
    'contact/receipts/',     # فیشی که از فرم تماس می‌آید
    'requests/',             # پیوست درخواست دانشجو
    'submissions/',          # پاسخ تکلیف
    'lifecycle/',            # مرخصی، انصراف، مهمانی
)

# کدام مدل و کدام فیلد، و پرونده مالِ چه کسی است.
#
# \u200ENone\u200E یعنی صاحبِ کاربری ندارد (داوطلب هنوز حساب ندارد، فرستندهٔ فرم
# تماس هم همین‌طور)، پس فقط کارمند می‌بیند.
OWNERS = (
    ('dashboard', 'Payment', 'receipt_file', 'student'),
    ('dashboard', 'StudentRequest', 'file', 'student'),
    ('dashboard', 'AssignmentSubmission', 'file', 'student'),
    ('dashboard', 'StudentDiscountClaim', 'document', 'student'),
    ('dashboard', 'StudentLifecycleRequest', 'attachment', 'student'),
    ('admissions', 'Application', 'doc_national_id', None),
    ('admissions', 'Application', 'doc_prev_degree', None),
    ('admissions', 'Application', 'doc_photo', None),
    ('admissions', 'Application', 'doc_military', None),
    ('admissions', 'StudentPayment', 'receipt', None),
    ('contact', 'ContactMessage', 'attachment', None),
)


def is_private(name: str) -> bool:
    """آیا این نشانی زیر یکی از پوشه‌های حساس است؟"""
    clean = (name or '').lstrip('/')
    return any(clean.startswith(prefix) for prefix in PRIVATE_PREFIXES)


@deconstructible
class private_upload_to:                      # noqa: N801 - مثل تابع صدا می‌شود
    """نامِ تصادفی، با همان پسوند.

    نام اصلی را نگه نمی‌داریم: هم حدس‌زدنی است، هم خودش اطلاعات لو
    می‌دهد — \u200Eکارت ملی احمدی.jpg\u200E پیش از باز شدن فایل هم گویاست.
    """
    def __init__(self, folder: str):
        self.folder = folder.strip('/')

    def __call__(self, instance, filename):   # noqa: ARG002 - امضای جنگو
        suffix = Path(filename or '').suffix.lower()[:10]
        return '%s/%s%s' % (self.folder, uuid.uuid4().hex, suffix)

    def __eq__(self, other):
        return (isinstance(other, private_upload_to)
                and other.folder == self.folder)

    def __hash__(self):
        return hash(('private_upload_to', self.folder))


def _staff(user) -> bool:
    return bool(user and user.is_authenticated
                and (user.is_staff or user.is_superuser))


def may_read(user, name: str) -> bool:
    """آیا این کاربر حق دیدن این پرونده را دارد؟"""
    if _staff(user):
        return True
    if not (user and user.is_authenticated):
        return False

    from django.apps import apps

    for app_label, model_name, field, owner in OWNERS:
        if owner is None:
            continue
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:                   # pragma: no cover - مدل جابه‌جا شده
            continue
        if model.objects.filter(**{field: name, owner: user}).exists():
            return True

    # استاد پاسخِ تکلیفِ درسِ خودش را می‌بیند؛ نمره‌دادن بدون دیدنش
    # ممکن نیست.
    try:
        submission = apps.get_model('dashboard', 'AssignmentSubmission')
    except LookupError:                       # pragma: no cover
        return False
    return submission.objects.filter(
        file=name, assignment__professor=user).exists()


def _safe_path(name: str) -> Path:
    """نشانی را به مسیر داخل \u200EMEDIA_ROOT\u200E تبدیل می‌کند، یا هیچ.

    \u200E..\u200E و مسیر مطلق اینجا می‌میرند؛ وگرنه \u200E/media/../config/settings.py\u200E
    یعنی خواندن کلید محرمانه.
    """
    root = Path(settings.MEDIA_ROOT).resolve()
    clean = posixpath.normpath('/' + (name or '')).lstrip('/')
    if not clean or clean.startswith('..'):
        raise SuspiciousFileOperation('مسیر نامعتبر: %r' % name)
    target = (root / clean).resolve()
    if target != root and root not in target.parents:
        raise SuspiciousFileOperation('مسیر بیرون از media: %r' % name)
    return target


def serve(request, path: str):
    """پرونده‌های پوشه‌های حساس را، فقط برای کسی که حق دارد."""
    if not is_private(path):
        # بقیهٔ \u200E/media/\u200E کار وب‌سرور است. اینجا پاسخ ندادن یعنی نشانیِ
        # جعلی هم چیزی از ساختار پوشه‌ها لو نمی‌دهد.
        raise Http404

    if not may_read(request.user, path.lstrip('/')):
        # نبودِ فایل و نداشتنِ حق، هر دو یک پاسخ می‌گیرند تا کسی با
        # تفاوتشان نتواند فهرست پرونده‌ها را بسازد.
        if request.user.is_authenticated:
            raise PermissionDenied
        raise Http404

    try:
        target = _safe_path(path)
    except SuspiciousFileOperation:
        raise Http404

    if not target.is_file():
        raise Http404

    response = FileResponse(target.open('rb'))
    # نه در کش میانی بماند، نه موتور جست‌وجو سراغش برود.
    response['Cache-Control'] = 'private, no-store'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    response['Content-Disposition'] = 'inline; filename="%s"' % (
        target.name.replace('"', ''))
    return response
