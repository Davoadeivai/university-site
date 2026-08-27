"""فایل‌هایی که در دیتابیس ثبت‌اند ولی روی سرور نیستند.

    python manage.py check_media_files
    python manage.py check_media_files --list

چرا لازم شد
───────────
روی سایت زنده، هر ۷۵ سند سرفصل و ده‌ها آیین‌نامه و فرم، نام فایل
در دیتابیس داشتند و خودِ فایل روی سرور نبود. بازدیدکننده روی
«دریافت» می‌زد و به صفحهٔ ۴۰۴ می‌رسید — و هیچ‌جای پنل نمی‌گفت چرا.

علتش هم منطقی است: `deploy.py` عمداً پوشهٔ media را کپی نمی‌کند تا
آنچه مدیر از پنل آپلود کرده پاک نشود. اما همین یعنی فایلی که فقط
روی کامپیوتر توسعه هست، هیچ‌وقت خودش به سرور نمی‌رسد.

قالب‌ها حالا دکمهٔ دانلودِ فایلِ نبوده را نشان نمی‌دهند، پس صفحه
دیگر ۴۰۴ نمی‌دهد؛ ولی فایل همچنان باید آپلود شود. این دستور
می‌گوید کدام‌ها.
"""
from __future__ import annotations

from collections import defaultdict

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db.models import FileField

from core.filecheck import file_present


class Command(BaseCommand):
    help = 'گزارش فایل‌های ثبت‌شده‌ای که روی سرور نیستند'

    def add_arguments(self, parser):
        parser.add_argument('--list', action='store_true',
                            help='نام تک‌تک فایل‌های گمشده را هم بنویس')
        parser.add_argument('--limit', type=int, default=15,
                            help='حداکثر چند نام از هر گروه نوشته شود')

    def handle(self, *args, **options):
        missing = defaultdict(list)
        total = 0

        for model in apps.get_models():
            names = [f.name for f in model._meta.fields
                     if isinstance(f, FileField)]
            if not names:
                continue
            label = model._meta.verbose_name or model.__name__
            for row in model.objects.all().iterator():
                for name in names:
                    field = getattr(row, name, None)
                    if not field:
                        continue          # خالی بودن ایراد نیست
                    total += 1
                    if not file_present(field):
                        missing['%s — %s' % (label, name)].append(field.name)

        if not missing:
            self.stdout.write(self.style.SUCCESS(
                'همهٔ %d فایل ثبت‌شده روی سرور هستند.' % total))
            return

        gone = sum(len(rows) for rows in missing.values())
        self.stdout.write(self.style.WARNING(
            '%d فایل از %d فایل ثبت‌شده روی سرور نیست:' % (gone, total)))

        for group, rows in sorted(missing.items(), key=lambda kv: -len(kv[1])):
            self.stdout.write('  %4d  %s' % (len(rows), group))
            if not options['list']:
                continue
            for path in rows[:options['limit']]:
                self.stdout.write('          %s' % path)
            if len(rows) > options['limit']:
                self.stdout.write('          … و %d مورد دیگر'
                                  % (len(rows) - options['limit']))

        self.stdout.write('')
        self.stdout.write('این فایل‌ها با دیپلوی منتقل نمی‌شوند — دیپلوی عمداً')
        self.stdout.write('پوشهٔ media را دست نمی‌زند تا آپلودهای پنل پاک نشوند.')
        self.stdout.write('از cPanel ← File Manager پوشهٔ media را آپلود کنید،')
        self.stdout.write('یا همان فایل‌ها را از پنل ادمین دوباره بگذارید.')
