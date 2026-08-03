"""پاک‌سازی نام موسسه و نام شهر قدیمی از رکوردهای پایگاه داده.

نام موسسه همه‌جا باید دقیقاً «موسسه آموزش عالی علامه امینی» باشد، بدون
هیچ پسوند شهری. تغییر قالب‌ها کافی نیست: عنوان، نشانی و متن‌های محتوایی
در پایگاه داده ذخیره شده‌اند و از پنل ادمین می‌آیند.

    python manage.py clean_institute_name            # فقط گزارش
    python manage.py clean_institute_name --apply    # اعمال تغییر
"""
from django.core.management.base import BaseCommand
from django.db import transaction

INSTITUTE = 'موسسه آموزش عالی علامه امینی'

# ترتیب مهم است: اول شکل‌های ترکیبی نام+شهر، بعد خودِ واژهٔ شهر
REPLACEMENTS = [
    ('موسسه آموزش عالی علامه امینی بهنمیر', INSTITUTE),
    ('موسسه آموزش عالی علامه امینی - بهنمیر', INSTITUTE),
    ('مؤسسه آموزش عالی علامه امینی بهنمیر', INSTITUTE),
    ('مؤسسه آموزش عالی علامه امینی - بهنمیر', INSTITUTE),
    ('علامه امینی بهنمیر', 'علامه امینی'),
    ('علامه امینی - بهنمیر', 'علامه امینی'),
    ('بابلسر - بهنمیر', 'بابلسر'),
    ('بهنمیر', 'بابلسر'),
]

# (اپ.مدل, [فیلدهای متنی])
TARGETS = [
    ('core.SiteSettings', ['university_name_fa', 'university_name_en',
                           'address', 'about_short']),
    ('core.CityInfo', ['title', 'description']),
    ('core.CityAttraction', ['name', 'description', 'category']),
    ('core.QuickLink', ['title']),
    ('core.Event', ['title', 'description', 'location']),
    ('core.FAQ', ['question', 'answer']),
    ('core.InstitutionGoal', ['title', 'description']),
    ('core.PressRelease', ['title', 'content']),
    ('core.DownloadableDocument', ['title', 'description']),
    ('news.News', ['title', 'summary', 'content']),
    ('academics.Department', ['name', 'description']),
    ('academics.Major', ['name', 'description']),
    ('accounts.Announcement', ['title', 'content']),
]


class Command(BaseCommand):
    help = 'حذف پسوند شهر از نام موسسه در رکوردهای پایگاه داده'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='بدون این گزینه فقط گزارش می‌دهد')

    def handle(self, *args, **options):
        from django.apps import apps

        apply_changes = options['apply']
        total_rows = total_fields = 0

        for label, fields in TARGETS:
            try:
                model = apps.get_model(label)
            except LookupError:
                continue

            existing = {f.name for f in model._meta.get_fields()
                        if hasattr(f, 'attname')}
            fields = [f for f in fields if f in existing]
            if not fields:
                continue

            for obj in model.objects.all():
                dirty = []
                for field in fields:
                    value = getattr(obj, field, None)
                    if not isinstance(value, str) or not value:
                        continue
                    new = value
                    for old, repl in REPLACEMENTS:
                        new = new.replace(old, repl)
                    if new != value:
                        setattr(obj, field, new)
                        dirty.append(field)

                if not dirty:
                    continue
                total_rows += 1
                total_fields += len(dirty)
                self.stdout.write('  %s#%s → %s' % (
                    label, obj.pk, '، '.join(dirty)))
                if apply_changes:
                    with transaction.atomic():
                        obj.save(update_fields=dirty)

        if not total_rows:
            self.stdout.write(self.style.SUCCESS(
                'هیچ رکوردی نیاز به اصلاح ندارد.'))
            return

        if apply_changes:
            self.stdout.write(self.style.SUCCESS(
                '\n%d رکورد و %d فیلد اصلاح شد.' % (total_rows, total_fields)))
        else:
            self.stdout.write(self.style.WARNING(
                '\n%d رکورد و %d فیلد نیاز به اصلاح دارند. '
                'برای اعمال، دوباره با --apply اجرا کنید.'
                % (total_rows, total_fields)))
