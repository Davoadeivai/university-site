"""دکمهٔ «رشته‌های پذیرش دانشجو» را روی یک اسلاید می‌گذارد.

    python manage.py set_slide_cta
    python manage.py set_slide_cta --slide 3
    python manage.py set_slide_cta --clear

چرا لازم شد
───────────
داوطلبی که صفحهٔ اصلی را باز می‌کند، هفت عکس می‌بیند و هیچ نشانه‌ای
از اینکه موسسه چه رشته‌هایی دارد. این یک دکمه، همان چیزی است که او
دنبالش آمده.

فقط یک اسلاید
─────────────
دکمه روی هر هفت اسلاید، هفت بار همان حرف است. این دستور اول همهٔ
دکمه‌ها را برمی‌دارد و بعد روی یکی می‌گذارد، پس اجرای دوباره
دکمه‌های پراکنده جا نمی‌گذارد.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.urls import reverse

from core.models import Slider

LABEL = 'رشته‌های پذیرش دانشجو'


class Command(BaseCommand):
    help = 'گذاشتن دکمهٔ رشته‌های پذیرش روی یک اسلاید'

    def add_arguments(self, parser):
        parser.add_argument(
            '--slide', type=int, default=1,
            help='چندمین اسلاید (پیش‌فرض: اولی)')
        parser.add_argument(
            '--label', default=LABEL, help='متن دکمه')
        parser.add_argument(
            '--clear', action='store_true',
            help='دکمه را از همهٔ اسلایدها بردار')

    def handle(self, *args, **options):
        slides = list(Slider.objects.filter(is_active=True).order_by('order'))
        if not slides:
            self.stdout.write(self.style.WARNING(
                'اسلایدی ثبت نشده — اول import_slides را بزنید.'))
            return

        # هر دکمهٔ قبلی برداشته می‌شود تا تکراری نماند
        cleared = 0
        for slide in slides:
            if slide.link_text or slide.link:
                slide.link_text = ''
                slide.link = ''
                slide.save(update_fields=['link_text', 'link'])
                cleared += 1

        if options['clear']:
            self.stdout.write(self.style.SUCCESS(
                'دکمه از %d اسلاید برداشته شد.' % cleared))
            return

        index = max(1, min(options['slide'], len(slides))) - 1
        target = slides[index]
        target.link_text = options['label']
        target.link = reverse('academics:majors')
        target.save(update_fields=['link_text', 'link'])

        self.stdout.write(self.style.SUCCESS('انجام شد:'))
        self.stdout.write('  اسلاید %d ← «%s»' % (index + 1, target.link_text))
        self.stdout.write('  مقصد: %s' % target.link)
        if cleared > 1:
            self.stdout.write('  %d دکمهٔ قبلی برداشته شد' % (cleared - 1))
