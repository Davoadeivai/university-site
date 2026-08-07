"""پر کردن کد رشته، تعداد واحد و ساعت کارآموزی از سند رسمی.

چرا لازم بود
────────────
۴۶ رشته از ۵۵ رشتهٔ سایت `total_credits=0` داشتند — یعنی صفحهٔ هر
رشته «تعداد واحد: ۰» نشان می‌داد. کد رسمی وزارت هم اصلاً جایی ذخیره
نمی‌شد، در حالی که داوطلب در دفترچهٔ سنجش با همان کد رشته را پیدا
می‌کند و اولین چیزی است که دنبالش می‌گردد.

تطبیق نام
─────────
سند و دیتابیس یک رشته را جور دیگری می‌نویسند: «مدیریت بازرگانی
(گرایش بازاریابی)» در برابر «مدیریت بازرگانی - گرایش بازاریابی»، یا
«الکتروتکنیک (برق صنعتی)» در برابر «الکتروتکنیک برق صنعتی». پس
مقایسه روی مجموعهٔ واژه‌ها انجام می‌شود، نه روی رشتهٔ خام — و فقط
داخل همان مقطع، تا «حسابداری» کاردانی با «حسابداری» ارشد قاطی نشود.

هرچه تطبیق نخورد گزارش می‌شود و دست‌نخورده می‌ماند؛ حدس‌زدن روی
کد رسمی یک رشته بدتر از خالی گذاشتنش است.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from academics.models import Major

DATA_FILE = Path(__file__).resolve().parents[2] / 'seed_data' / 'major_codes.json'

# نام مقطع در سند → مقدار فیلد degree
LEVELS = {
    'کارشناسی ارشد': 'master',
    'کارشناسی پیوسته': 'bachelor_cont',
    'کارشناسی ناپیوسته': 'bachelor_disc',
    'کاردانی پیوسته': 'associate_cont',
    'کاردانی ناپیوسته': 'associate_disc',
    'کاردانی فنی': 'associate_tech',
}

# وقتی در مقطع دقیق چیزی پیدا نشد، این مقطع‌ها هم گشته می‌شوند
DEGREE_FALLBACK = {
    'associate_disc': ('associate_cont', 'associate_tech', 'associate'),
    'associate_cont': ('associate_disc', 'associate_tech'),
    'bachelor_disc': ('bachelor',),
    'bachelor_cont': ('bachelor',),
}

# واژه‌هایی که در تطبیق وزن ندارند و فقط سبک نگارش‌اند
NOISE = {'گرایش', 'رشته', 'مقطع', 'و', 'ـ', '-', '–'}
_PUNCT = re.compile(r'[()\[\]«»٫,.\-–_/\\]+')


def tokens(name: str) -> frozenset:
    """نام را به مجموعهٔ واژه‌های معنادار تبدیل می‌کند."""
    cleaned = _PUNCT.sub(' ', name or '')
    cleaned = cleaned.replace('ي', 'ی').replace('ك', 'ک').replace('‌', ' ')
    return frozenset(w for w in cleaned.split() if w and w not in NOISE)


def best_match(record, candidates):
    """نزدیک‌ترین رشتهٔ هم‌مقطع، یا None اگر شباهت کافی نبود.

    معیار: واژه‌های مشترک تقسیم بر بزرگ‌ترین طرف. تقسیم بر کوچک‌ترین
    طرف وسوسه‌انگیز است ولی غلط: «حسابداری» تک‌واژه‌ای آن‌وقت با
    «حسابداری و بازرگانی» صددرصد جور درمی‌آمد و کد یک رشته روی رشتهٔ
    دیگری می‌نشست. با بزرگ‌ترین طرف، آن نسبت ۵۰٪ می‌شود و رد.

    آستانهٔ ۰٫۷ هم «مهندسی برق – قدرت» را از «تکنولوژی مهندسی برق»
    جدا نگه می‌دارد.
    """
    wanted = tokens(record['name'])
    if not wanted:
        return None, 0.0
    best, score = None, 0.0
    for major in candidates:
        have = tokens(major.name)
        if not have:
            continue
        shared = len(wanted & have)
        ratio = shared / max(len(wanted), len(have))
        # مساوی‌ها را با کمترین اختلاف طول می‌شکنیم تا نام دقیق‌تر ببرد
        if ratio > score or (ratio == score and best is not None
                             and abs(len(have) - len(wanted))
                             < abs(len(tokens(best.name)) - len(wanted))):
            best, score = major, ratio
    return (best, score) if score >= 0.7 else (None, score)


class Command(BaseCommand):
    help = 'پر کردن کد رشته، واحد فارغ‌التحصیلی و ساعت کارآموزی از سند رسمی'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', help='فقط گزارش بده')
        parser.add_argument(
            '--overwrite', action='store_true',
            help='مقادیر موجود را هم بازنویسی کن (پیش‌فرض: فقط جای خالی)')

    @transaction.atomic
    def handle(self, *args, **options):
        if not DATA_FILE.exists():
            self.stderr.write('فایل داده پیدا نشد: %s' % DATA_FILE)
            return

        records = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        dry, overwrite = options['dry_run'], options['overwrite']

        filled = skipped = 0
        unmatched: list[str] = []
        used: set = set()

        for record in records:
            degree = LEVELS.get(record['level'])
            if degree is None:
                unmatched.append('%s — مقطع ناشناخته: %s'
                                 % (record['name'], record['level']))
                continue

            pool = [m for m in Major.objects.filter(degree=degree)
                    if m.pk not in used]
            major, score = best_match(record, pool)

            # سایت پنج رشتهٔ «کاردانی ناپیوسته» سند را با برچسب
            # «کاردانی پیوسته» ثبت کرده. این ناهماهنگی برچسب است، نه
            # نبودِ رشته — پس اگر در مقطع دقیق چیزی پیدا نشد، مقطع
            # هم‌خانواده هم گشته می‌شود.
            if major is None:
                for alt in DEGREE_FALLBACK.get(degree, ()):
                    pool = [m for m in Major.objects.filter(degree=alt)
                            if m.pk not in used]
                    major, alt_score = best_match(record, pool)
                    if major is not None:
                        score = alt_score
                        break
            if major is None:
                unmatched.append('%s (%s) — نزدیک‌ترین شباهت %.0f%%'
                                 % (record['name'], record['level'], score * 100))
                continue

            used.add(major.pk)
            changes = []
            for field, value in (('code', record['code']),
                                 ('total_credits', record['credits']),
                                 ('internship_hours', record['internship'])):
                if not value:
                    continue
                current = getattr(major, field)
                if current and not overwrite:
                    continue
                if current == value:
                    continue
                changes.append('%s: %s → %s' % (field, current or '—', value))
                if not dry:
                    setattr(major, field, value)

            if changes:
                if not dry:
                    major.save(update_fields=['code', 'total_credits',
                                              'internship_hours'])
                filled += 1
                self.stdout.write('  %-44s %s' % (
                    major.name[:43], '، '.join(changes)))
            else:
                skipped += 1

        verb = 'می‌شد پر کرد' if dry else 'پر شد'
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            '%d رشته %s، %d از قبل کامل بود.' % (filled, verb, skipped)))

        if unmatched:
            self.stdout.write(self.style.WARNING(
                '\n%d ردیف سند به هیچ رشته‌ای نخورد و دست‌نخورده ماند:'
                % len(unmatched)))
            for line in unmatched:
                self.stdout.write('  - %s' % line)
            self.stdout.write(
                'اگر این رشته‌ها در سایت هستند، نامشان با سند فرق دارد؛ '
                'کد و واحد را دستی در پنل ادمین بگذارید.')

        empty = Major.objects.filter(total_credits=0).count()
        if empty:
            self.stdout.write(
                '\n%d رشته هنوز تعداد واحدشان صفر است.' % empty)
        if dry:
            self.stdout.write('حالت آزمایشی بود — چیزی نوشته نشد.')
