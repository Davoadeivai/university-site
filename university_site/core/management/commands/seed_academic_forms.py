"""ثبت فرم‌های رسمی اداره آموزش در «آیین‌نامه‌ها و فرم‌ها».

فایل‌های PDF در `core/seed_files/forms/` نگهداری می‌شوند تا همراه گیت
جابه‌جا شوند؛ این دستور آن‌ها را داخل MEDIA_ROOT کپی می‌کند و برای هرکدام
یک رکورد DownloadableDocument می‌سازد.

چرا فایل‌ها در مخزن‌اند و نه فقط در media؟ چون دیپلوی عمداً پوشهٔ media را
دست نمی‌زند (تا عکس‌های آپلودی پاک نشوند). پس فرم‌هایی که بخشی از خود
پروژه‌اند باید از مسیر کد به سرور برسند.

    python manage.py seed_academic_forms
    python manage.py seed_academic_forms --replace   # فایل و عنوان را هم بازنویسی کن
"""
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

# (نام فایل, عنوان, دسته, مقطع, ترتیب, توضیح)
FORMS = [
    ('add-drop-form.pdf',
     'برگه حذف و اضافه واحد',
     'form', 'general', 10,
     'برای حذف یا اضافه کردن درس در بازهٔ حذف و اضافه. حداکثر ۲ عنوان حذف و ۲ عنوان اضافه.'),

    ('emergency-course-drop.pdf',
     'فرم درخواست حذف تک‌درس (حذف اضطراری)',
     'form', 'general', 20,
     'حذف یک درس بدون احتساب در سنوات، با تأیید استاد و مدیر آموزش. واحدهای باقیمانده نباید زیر ۱۲ برسد.'),

    ('academic-leave-request.pdf',
     'برگ درخواست مرخصی تحصیلی',
     'form', 'general', 30,
     'درخواست مرخصی برای یک نیمسال، با تأیید مدیر گروه و معاونت آموزشی.'),

    ('academic-issues-request.pdf',
     'فرم درخواست بررسی مسائل آموزشی',
     'form', 'general', 40,
     'طرح هر مشکل آموزشی برای بررسی در معاونت آموزشی موسسه.'),

    ('equivalent-degree-request.pdf',
     'فرم درخواست مدرک معادل (کاردانی)',
     'form', 'general', 50,
     'ویژهٔ دانشجوی محروم از تحصیل کارشناسی پیوسته با حداقل ۶۸ واحد گذرانده و معدل کل ۱۲ به بالا.'),

    ('exam-misconduct-undertaking.pdf',
     'تعهدنامه تخلف امتحانی',
     'form', 'general', 60,
     'تعهد کتبی پس از اولین تخلف در جلسهٔ امتحان، با امضا و اثر انگشت.'),

    ('exam-absence-request.pdf',
     'فرم حاضر نشدن سر جلسهٔ امتحان',
     'form', 'general', 70,
     'اعلام علت غیبت در جلسهٔ امتحان به اداره امتحانات، همراه فهرست دروس.'),

    ('internship-request.pdf',
     'فرم شمارهٔ ۱ — درخواست معرفی برای کارآموزی',
     'form', 'general', 80,
     'گام اول کارآموزی: تأیید انتخاب واحد کارآموزی توسط آموزش و مدیر گروه.'),

    ('internship-introduction.pdf',
     'نمونه نامهٔ معرفی دانشجو به محل کارآموزی',
     'guide', 'general', 90,
     'نمونهٔ نامهٔ معرفی که پس از تأیید فرم شمارهٔ ۱ صادر می‌شود.'),

    ('clearance-withdrawal.pdf',
     'فرم تسویه حساب دانشجویان (انتقالی، انصرافی، اخراجی، تغییر رشته)',
     'form', 'general', 100,
     'تسویه حساب هنگام ترک تحصیل یا جابه‌جایی؛ نیازمند تأیید کتابخانه، امور مالی، رفاه و نظام وظیفه.'),

    ('clearance-graduate-bachelor.pdf',
     'فرم تسویه حساب فارغ‌التحصیلان (کاردانی و کارشناسی)',
     'form', 'general', 110,
     'تسویه حساب پایان تحصیل برای مقاطع کاردانی و کارشناسی.'),

    ('clearance-graduate-master.pdf',
     'فرم تسویه حساب فارغ‌التحصیلان کارشناسی ارشد',
     'form', 'master', 120,
     'تسویه حساب پایان تحصیل ویژهٔ کارشناسی ارشد، شامل تأیید اداره پژوهش.'),
]

SEED_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'seed_files', 'forms',
)
MEDIA_SUBDIR = 'documents'


class Command(BaseCommand):
    help = 'ثبت فرم‌های رسمی اداره آموزش در بخش «آیین‌نامه‌ها و فرم‌ها»'

    def add_arguments(self, parser):
        parser.add_argument(
            '--replace', action='store_true',
            help='عنوان، توضیح و فایل رکوردهای موجود را هم بازنویسی کن',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from core.models import DownloadableDocument

        replace = options['replace']
        dest_dir = os.path.join(settings.MEDIA_ROOT, MEDIA_SUBDIR)
        os.makedirs(dest_dir, exist_ok=True)

        created = updated = skipped = missing = 0

        for name, title, category, degree, order, desc in FORMS:
            source = os.path.join(SEED_DIR, name)
            if not os.path.isfile(source):
                self.stdout.write(self.style.ERROR('  ! فایل پیدا نشد: %s' % name))
                missing += 1
                continue

            target = os.path.join(dest_dir, name)
            if replace or not os.path.exists(target):
                shutil.copyfile(source, target)

            obj = DownloadableDocument.objects.filter(title=title).first()
            rel_path = '%s/%s' % (MEDIA_SUBDIR, name)

            if obj is None:
                DownloadableDocument.objects.create(
                    title=title, category=category, degree_level=degree,
                    description=desc, file=rel_path, order=order, is_active=True,
                )
                created += 1
                self.stdout.write('  + %s' % title)
            elif replace:
                obj.category = category
                obj.degree_level = degree
                obj.description = desc
                obj.file = rel_path
                obj.order = order
                obj.is_active = True
                obj.save()
                updated += 1
                self.stdout.write('  ~ %s' % title)
            else:
                # ویرایش ادمین نباید بی‌اجازه بازنویسی شود
                skipped += 1
                self.stdout.write('  = %s (دست‌نخورده)' % title)

        self.stdout.write(self.style.SUCCESS(
            '\n%d جدید، %d به‌روز، %d دست‌نخورده%s.' % (
                created, updated, skipped,
                '، %d فایل گم‌شده' % missing if missing else '',
            )
        ))
        self.stdout.write(
            'مسیر نمایش در سایت: بخش «آیین‌نامه‌ها و فرم‌ها»\n'
            'ویرایش از پنل: /admin/core/downloadabledocument/'
        )
