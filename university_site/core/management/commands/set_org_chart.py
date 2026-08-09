"""نشاندن تصویر چارت سازمانی و پاک‌کردن درخت ناقص قبلی.

صفحهٔ «درباره موسسه» دو منبع برای چارت داشت:

  ۱. `SiteSettings.org_chart_file` — یک فایل تصویر یا PDF
  ۲. `OrganizationalChart` — یک درخت گره‌به‌گره در دیتابیس

قالب اولی را ترجیح می‌دهد و فقط اگر خالی بود سراغ دومی می‌رود. فایل
خالی بود و درخت هفت گره داشت — ریاست، دو معاونت و چهار دبیرخانه —
یعنی بازدیدکننده چارتی می‌دید که پنج معاونت و ده‌ها واحد موسسه در آن
نبود. ناقص‌بودنش از نبودنش گمراه‌کننده‌تر بود.

چارت رسمی موسسه یک تصویر است، پس همان می‌نشیند و از این پس روی صفحه
دیده می‌شود. گره‌های درختی پاک نمی‌شوند: قالب وقتی فایل هست سراغشان
نمی‌رود، پس روی سایت دیده نمی‌شوند ولی در پنل ادمین باقی می‌مانند.
حذف داده کاری است که باید صریح خواسته شود — با `--drop-nodes`.
"""
from __future__ import annotations

from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import OrganizationalChart, SiteSettings

IMAGE = Path(__file__).resolve().parents[2] / 'seed_files' / 'org-chart.jpg'


class Command(BaseCommand):
    help = 'نشاندن تصویر چارت سازمانی در صفحهٔ «درباره موسسه»'

    def add_arguments(self, parser):
        parser.add_argument(
            '--drop-nodes', action='store_true',
            help='گره‌های درختی OrganizationalChart را هم حذف کن. '
                 'پیش‌فرض نیست: حذف داده کاری است که باید خواسته شود.')
        parser.add_argument(
            '--replace', action='store_true',
            help='اگر فایلی از قبل هست هم جایگزینش کن')

    @transaction.atomic
    def handle(self, *args, **options):
        if not IMAGE.exists():
            self.stderr.write('تصویر چارت پیدا نشد: %s' % IMAGE)
            return

        settings_row = SiteSettings.objects.first()
        if settings_row is None:
            self.stderr.write(
                'رکورد «تنظیمات سایت» وجود ندارد — اول در پنل ادمین بسازید.')
            return

        if settings_row.org_chart_file and not options['replace']:
            self.stdout.write(
                'چارت از قبل هست: %s' % settings_row.org_chart_file.name)
            self.stdout.write('برای جایگزینی، --replace بزنید.')
        else:
            if settings_row.org_chart_file:
                try:
                    settings_row.org_chart_file.delete(save=False)
                except OSError:
                    pass
            settings_row.org_chart_file.save(
                'org-chart.jpg', ContentFile(IMAGE.read_bytes()), save=True)
            self.stdout.write(self.style.SUCCESS(
                'تصویر چارت نشست: %s' % settings_row.org_chart_file.name))

        # ── درخت گره‌ای ──
        nodes = OrganizationalChart.objects.count()
        if not nodes:
            self.stdout.write('درخت گره‌ای از قبل خالی بود.')
        elif options['drop_nodes']:
            for node in OrganizationalChart.objects.all():
                self.stdout.write('  حذف گره: %s' % node.name)
            OrganizationalChart.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('%d گره حذف شد.' % nodes))
        else:
            self.stdout.write(
                '%d گره درختی دست‌نخورده ماند. چون فایل چارت هست، قالب '
                'همان را نشان می‌دهد و گره‌ها روی صفحه دیده نمی‌شوند — '
                'ولی در پنل ادمین سر جایشان هستند.' % nodes)

        self.stdout.write('')
        self.stdout.write('صفحهٔ چارت: /درباره-ما/#chart')
