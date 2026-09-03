"""مدیر هر گروه آموزشی را از فهرست افراد موسسه می‌نویسد.

    python manage.py set_group_heads --dry-run
    python manage.py set_group_heads
    python manage.py set_group_heads --replace

چرا لازم شد
───────────
یازده گروه آموزشی روی سایت بود و هیچ‌کدام مدیرش ثبت نشده بود؛ کارت
مدیر گروه خالی می‌ماند. اسم‌ها حدس نمی‌خواهند: خودِ موسسه ده مدیر
گروه را در «افراد موسسه ← مدیران گروه آموزشی» ثبت کرده، هرکدام با
سمتش — «مدیر گروه حسابداری»، «مدیر گروه برق و کامپیوتر» و مانند
این‌ها.

این دستور همان سمت را می‌خواند و هر مدیر را کنار گروه خودش
می‌گذارد. اگر همان شخص در «اعضای هیئت علمی» هم پرونده داشته باشد،
به‌جای متن به آن پرونده وصل می‌شود — یعنی عکس و مرتبهٔ علمی و راه
تماسش خودکار روی صفحهٔ گروه می‌آید و با هر به‌روزرسانی تازه می‌ماند.

تطبیق چگونه است
────────────────
از سمت، عبارت «مدیر گروه» برداشته می‌شود و باقی‌اش به واژه‌ها
شکسته می‌شود: «برق و کامپیوتر» می‌شود «برق» و «کامپیوتر». هر واژه
با نام گروه‌ها سنجیده می‌شود، و واژهٔ بلندتر جلوتر است تا «مدیریت
بازرگانی» پیش از «مدیریت» بنشیند.

هر گروه یک نام می‌گیرد، نه بیشتر. موسسه برای حسابداری و مدیریت
صنعتی دو نفر نوشته و اول هر دو نام کنار هم روی کارت می‌آمد؛ خواندنش
گیج‌کننده بود («مدیر گروه: الف و ب»). حالا نفر اولِ فهرست موسسه ثبت
می‌شود و نام دوم در گزارش پایان کار می‌آید تا اگر انتخاب درست او
بود، از پنل جایگزینش کنید.

مدیری که گروهش روی سایت نیست (مثل «مدیر گروه مدیریت» که میان سه
گروه پخش است) هم بی‌صدا کنار گذاشته نمی‌شود و در همان گزارش می‌آید.

مدیری که کسی دستی در پنل نوشته، جز با ‎--replace‎ دست نمی‌خورد.
"""
from __future__ import annotations

import re

from django.core.management.base import BaseCommand
from django.db import transaction

from academics.models import AcademicGroup
from directory.models import DirectoryPerson
from faculty.models import Professor

# اگر فهرست افراد هنوز پر نشده باشد (seed_directory اجرا نشده)،
# همین ده ردیف — همان‌طور که در سند موسسه آمده — به کار می‌رود.
FALLBACK = [
    ('جلال قنبری جلودار', 'مدیر گروه مدیریت آموزشی'),
    ('سجاد سالاری', 'مدیر گروه حسابداری'),
    ('فاطمه نمازی', 'مدیر گروه برق و کامپیوتر'),
    ('حسن عمرانی', 'مدیر گروه مکانیک و معماری'),
    ('علی فرنگی', 'مدیر گروه مدیریت'),
    ('مسعود باباخانی', 'مدیر گروه حسابداری'),
    ('هانیه دلیران چمن‌زمین', 'مدیر گروه مدیریت بازرگانی'),
    ('حسینعلی قربانی', 'مدیر گروه روانشناسی'),
    ('حسن فارسیجانی', 'مدیر گروه مدیریت صنعتی (ارشد)'),
    ('محمدرضا خسروی مقدم', 'مدیر گروه مدیریت صنعتی'),
]


def fold(text: str) -> str:
    """متن، بدون تفاوت‌های نوشتاری بی‌اهمیت."""
    cleaned = (text or '').replace('ي', 'ی').replace('ك', 'ک')
    for ch in ('‌', '‏', '‎', '،', '-', '–', '—', '(', ')'):
        cleaned = cleaned.replace(ch, ' ')
    return ''.join(cleaned.split())


def scope_words(position: str) -> list:
    """واژه‌های سمت، بدون «مدیر گروه» و بدون توضیح داخل پرانتز."""
    text = re.sub(r'\(.*?\)', ' ', position or '')
    text = text.replace('مدیریت گروه', ' ').replace('مدیر گروه', ' ')
    parts = re.split(r'\s+و\s+|—|–|/|،|,', text)
    return [fold(part) for part in parts if fold(part)]


def note_of(position: str) -> str:
    """توضیح داخل پرانتزِ سمت — مثل «(ارشد)»."""
    found = re.search(r'\((.*?)\)', position or '')
    return found.group(1).strip() if found else ''


class Command(BaseCommand):
    help = 'ثبت مدیر گروه‌ها از فهرست افراد موسسه'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='فقط بگو چه می‌شود، چیزی را عوض نکن')
        parser.add_argument('--replace', action='store_true',
                            help='مدیری که دستی ثبت شده را هم بازنویسی کن')

    def _heads(self):
        """نام و سمت مدیران گروه — از پنل، وگرنه از فهرست سند."""
        rows = [
            (person.display_name, person.position)
            for person in DirectoryPerson.objects.filter(
                category='group_head', is_active=True).order_by('order')
            if (person.position or '').strip()
        ]
        return rows or FALLBACK

    def handle(self, *args, **options):
        dry = options['dry_run']
        groups = list(AcademicGroup.objects.filter(is_active=True)
                      .select_related('department').order_by('order', 'name'))
        if not groups:
            self.stdout.write(self.style.WARNING('گروهی ثبت نشده.'))
            return

        folded = {group.pk: fold(group.name).replace('گروه', '')
                  for group in groups}

        # واژهٔ بلندتر اول: «مدیریتبازرگانی» پیش از «مدیریت»، وگرنه
        # نامِ عام، گروهِ خاص را می‌قاپد.
        placed = {}
        # طولِ واژه‌ای که هر گروه را گرفته. مدیرِ عام‌تر نباید گروهی
        # را که مدیرِ خاص‌ترش دارد بگیرد: «مدیر گروه مدیریت» نباید
        # کنار «مدیر گروه مدیریت بازرگانی» بنشیند. مساوی یعنی هم‌رتبه،
        # و موسسه برای حسابداری و مدیریت صنعتی واقعاً دو مدیر نوشته.
        claim = {}
        homeless = []
        ordered = sorted(
            self._heads(),
            key=lambda row: max((len(word) for word in scope_words(row[1])),
                                default=0),
            reverse=True)
        for name, position in ordered:
            words = scope_words(position)
            note = note_of(position)
            label = '%s (%s)' % (name, note) if note else name
            taken = False
            for group in groups:
                matched = [word for word in words if word in folded[group.pk]]
                if not matched:
                    continue
                weight = max(len(word) for word in matched)
                if weight < claim.get(group.pk, 0):
                    continue          # مدیرِ خاص‌تری این گروه را دارد
                claim[group.pk] = weight
                placed.setdefault(group.pk, []).append(label)
                taken = True
            if not taken:
                homeless.append((name, position))

        made = kept = linked = 0
        with transaction.atomic():
            for group in groups:
                names = placed.get(group.pk)
                if not names:
                    continue
                if (group.head_name or '').strip() and not options['replace']:
                    kept += 1
                    continue

                # یک نام، نه دو: «مدیر گروه: الف و ب» روی کارت
                # خوانده نمی‌شد. نفر دومِ فهرست موسسه در گزارش می‌آید.
                text = names[0]
                professor = self._professor_for(text)

                self.stdout.write('  %s → %s%s' % (
                    group.name, text, ' [هیئت علمی]' if professor else ''))
                made += 1
                if professor:
                    linked += 1
                if dry:
                    continue

                group.head = '' if professor else text
                group.head_professor = professor
                group.save(update_fields=['head', 'head_professor'])

        self.stdout.write(self.style.SUCCESS(
            'پیش‌نمایش:' if dry else 'انجام شد:'))
        self.stdout.write('  %d گروه مدیر %s' % (
            made, 'می‌گیرد' if dry else 'گرفت'))
        if linked:
            self.stdout.write(
                '  %d از آن‌ها به پروندهٔ هیئت علمی وصل شد' % linked)
        if kept:
            self.stdout.write('  %d گروه مدیرِ ثبت‌شده داشت و دست نخورد '
                              '(با --replace بازنویسی می‌شود)' % kept)
        for group in groups:
            for name in (placed.get(group.pk) or [])[1:]:
                self.stdout.write(
                    '  «%s» هم برای %s نوشته شده؛ نفر اول ثبت شد.'
                    % (name, group.name))
        without = [group.name for group in groups if group.pk not in placed]
        if without:
            self.stdout.write('  بدون مدیر ماند: %s' % '، '.join(without))
        for name, position in homeless:
            self.stdout.write(
                '  «%s» با سمت «%s» گروهی روی سایت ندارد.' % (name, position))

    def _professor_for(self, label: str):
        """پروندهٔ هیئت علمی همین شخص، اگر باشد."""
        target = fold(re.sub(r'\(.*?\)', '', label))
        for professor in Professor.objects.filter(is_active=True):
            if fold(professor.get_full_name()) == target:
                return professor
        return None
