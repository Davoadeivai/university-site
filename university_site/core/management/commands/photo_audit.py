"""گزارش وضعیت همهٔ تصویرهای سایت.

    python manage.py photo_audit

سه چیز را جدا می‌کند، چون سه مشکل متفاوت‌اند:

  «خالی»    فیلد تصویر پر نشده — جای عکس روی سایت خالی می‌ماند.
  «گم‌شده»  رکورد به فایلی اشاره می‌کند که روی دیسک نیست — بدترین
            حالت، چون در پنل ادمین «عکس دارد» دیده می‌شود ولی
            بازدیدکننده تصویر شکسته می‌بیند.
  «جای‌نما» متن راهنما به‌جای محتوای واقعی نشسته.

هیچ چیزی را عوض نمی‌کند.
"""
from __future__ import annotations

import os

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models

# مدل‌هایی که تصویرشان روی صفحه‌های عمومی دیده می‌شود، به‌ترتیب
# اهمیت برای بازدیدکننده.
WATCHED = [
    ('core', 'PresidencyOffice', 'صفحهٔ ریاست'),
    ('core', 'VicePresidency', 'صفحهٔ معاونت‌ها'),
    ('core', 'SecurityOffice', 'صفحهٔ حراست'),
    ('core', 'BoardMember', 'هیات موسس و امنا'),
    ('core', 'PresidencyOfficeUnit', 'واحدهای دفتر ریاست'),
    ('directory', 'DirectoryPerson', 'دفترچه تلفن و اعضای موسسه'),
    ('faculty', 'Professor', 'صفحهٔ اساتید'),
    ('core', 'Slider', 'اسلایدر صفحهٔ اصلی'),
    ('core', 'HomeSection', 'بخش‌های صفحهٔ اصلی'),
    ('core', 'HomeFeature', 'ویژگی‌های صفحهٔ اصلی'),
    ('news', 'News', 'اخبار'),
    ('core', 'Event', 'رویدادها'),
    ('academics', 'Department', 'دانشکده‌ها'),
    ('academics', 'AcademicGroup', 'گروه‌های آموزشی'),
]


def image_fields(model):
    return [f for f in model._meta.get_fields()
            if isinstance(f, models.ImageField)]


def is_placeholder(text: str) -> bool:
    value = (text or '').strip()
    return value.startswith('[') and value.endswith(']')


class Command(BaseCommand):
    help = 'گزارش تصویرهای خالی، گم‌شده و متن‌های جای‌نما'

    def add_arguments(self, parser):
        parser.add_argument(
            '--missing-only', action='store_true',
            help='فقط فایل‌های گم‌شده را نشان بده',
        )

    def handle(self, *args, **options):
        media_root = str(settings.MEDIA_ROOT)
        only_missing = options['missing_only']

        self.stdout.write('MEDIA_ROOT: %s\n' % media_root)

        total_missing = total_empty = 0
        placeholders: list[str] = []

        for app_label, model_name, where in WATCHED:
            try:
                model = apps.get_model(app_label, model_name)
            except LookupError:
                continue

            fields = image_fields(model)
            if not fields:
                continue

            rows = list(model.objects.all())
            if not rows:
                if not only_missing:
                    self.stdout.write('  %-26s %s' % (
                        model_name, self.style.WARNING('هیچ رکوردی ندارد — %s خالی است' % where)))
                continue

            for field in fields:
                empty, missing, filled = 0, [], 0
                for obj in rows:
                    value = getattr(obj, field.name, None)
                    if not value:
                        empty += 1
                        continue
                    path = os.path.join(media_root, value.name)
                    if os.path.exists(path):
                        filled += 1
                    else:
                        missing.append('%s → %s' % (obj, value.name))

                total_empty += empty
                total_missing += len(missing)

                if only_missing and not missing:
                    continue

                label = '%s.%s' % (model_name, field.name)
                summary = '%d دارد' % filled
                if empty:
                    summary += '، %d خالی' % empty
                if missing:
                    summary += '، %d گم‌شده' % len(missing)

                style = (self.style.ERROR if missing
                         else self.style.WARNING if empty
                         else self.style.SUCCESS)
                self.stdout.write('  %-34s %-28s %s' % (
                    label, style(summary), where))
                for line in missing[:8]:
                    self.stdout.write('      !! %s' % line)
                if len(missing) > 8:
                    self.stdout.write('      … و %d مورد دیگر' % (len(missing) - 8))

            # متن‌های جای‌نما — عکس نیستند ولی همان‌قدر روی صفحه بد دیده می‌شوند
            for obj in rows:
                for field in obj._meta.fields:
                    if not isinstance(field, (models.CharField, models.TextField)):
                        continue
                    if isinstance(field, models.ImageField):
                        continue
                    if is_placeholder(getattr(obj, field.name, '') or ''):
                        placeholders.append('%s.%s' % (model_name, field.name))

        self.stdout.write('')
        if total_missing:
            self.stdout.write(self.style.ERROR(
                '%d فایل گم‌شده — این‌ها روی سایت تصویر شکسته می‌دهند.'
                % total_missing))
        else:
            self.stdout.write(self.style.SUCCESS(
                'هیچ فایل گم‌شده‌ای نیست؛ هر رکوردی که عکس دارد، فایلش هم هست.'))

        if not only_missing:
            self.stdout.write('%d فیلد تصویر خالی است.' % total_empty)
            if placeholders:
                unique = sorted(set(placeholders))
                self.stdout.write(self.style.WARNING(
                    '\n%d فیلد هنوز متن راهنما دارد به‌جای محتوای واقعی:'
                    % len(unique)))
                for name in unique:
                    self.stdout.write('  - %s' % name)
