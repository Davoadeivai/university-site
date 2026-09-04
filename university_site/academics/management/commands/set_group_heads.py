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

گروهی که دو مدیر دارد، دو مدیر می‌گیرد. موسسه برای «حسابداری» و
«مدیریت صنعتی و مالی» دو نفر نوشته؛ اول هر دو نام در یک خط کنار هم
می‌آمد («مدیر گروه: الف و ب»)، بعد نفر دوم کنار گذاشته شد، و حالا
هرکدام ردیف خودش را دارد — با عکس، مرتبه و راه تماس جداگانه.

مدیری که گروهش روی سایت نیست (مثل «مدیر گروه مدیریت» که میان سه
گروه پخش است) هم بی‌صدا کنار گذاشته نمی‌شود و در همان گزارش می‌آید.

گروهی که مدیرش در پنل دست‌کاری شده — تیک «مدیر گروه دستی تنظیم
شده» — جز با ‎--replace‎ دست نمی‌خورد. آن تیک با هر ویرایشِ مدیر
گروه در پنل خودکار زده می‌شود، تا حذف یا اصلاحِ دستی با
به‌روزرسانی بعدی برنگردد.
"""
from __future__ import annotations

import re

from django.core.management.base import BaseCommand
from django.db import transaction

from academics.models import AcademicGroup, GroupHead
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


def note_of_label(label: str) -> str:
    """توضیح داخل پرانتزِ برچسبِ ساخته‌شده — «الف (ارشد)» → «ارشد»."""
    found = re.search(r'\((.*?)\)', label or '')
    return found.group(1).strip() if found else ''


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

    def _honorifics(self):
        """پیشوندِ هر نام، همان‌طور که در فهرست افراد ثبت شده."""
        table = {}
        for person in DirectoryPerson.objects.filter(
                category='group_head', is_active=True):
            title = (person.honorific or '').strip()
            if title:
                table[person.display_name] = title
        return table

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

        honorifics = self._honorifics()
        made = kept = linked = 0
        with transaction.atomic():
            for group in groups:
                names = placed.get(group.pk)
                if not names:
                    continue

                # تصمیمِ مدیر سایت — چه ویرایش، چه حذف — با
                # به‌روزرسانی بعدی برنمی‌گردد.
                if group.head_locked and not options['replace']:
                    kept += 1
                    continue

                self.stdout.write('  %s → %s' % (
                    group.name, '، '.join(names)))
                made += 1
                if dry:
                    linked += sum(
                        1 for label in names if self._professor_for(label))
                    continue

                # فیلدهای تکیِ قدیمی خالی می‌شوند و همه‌چیز به
                # ردیف‌های مدیران می‌رود؛ وگرنه یک گروه دو منبع
                # می‌داشت و دیر یا زود با هم اختلاف پیدا می‌کردند.
                group.group_heads.all().delete()
                for index, label in enumerate(names):
                    professor = self._professor_for(label)
                    if professor:
                        linked += 1
                    # برچسب ممکن است توضیح داشته باشد — «الف (ارشد)».
                    # پیشوند با نامِ خالی جست‌وجو می‌شود، وگرنه هیچ‌وقت
                    # پیدا نمی‌شد.
                    bare = re.sub(r'\s*\(.*?\)', '', label).strip()
                    GroupHead.objects.create(
                        group=group,
                        professor=professor,
                        name='' if professor else bare,
                        note=note_of_label(label),
                        honorific=honorifics.get(bare, ''),
                        order=index,
                    )
                if group.head or group.head_professor_id or group.head_photo:
                    group.head = ''
                    group.head_professor = None
                    group.head_photo = None
                    group.save(update_fields=[
                        'head', 'head_professor', 'head_photo'])

        self.stdout.write(self.style.SUCCESS(
            'پیش‌نمایش:' if dry else 'انجام شد:'))
        self.stdout.write('  %d گروه مدیر %s' % (
            made, 'می‌گیرد' if dry else 'گرفت'))
        if linked:
            self.stdout.write(
                '  %d مدیر به پروندهٔ هیئت علمی وصل شد' % linked)
        if kept:
            self.stdout.write('  %d گروه مدیرش در پنل تنظیم شده و دست نخورد '
                              '(با --replace بازنویسی می‌شود)' % kept)
        for group in groups:
            names = placed.get(group.pk) or []
            if len(names) > 1:
                self.stdout.write(
                    '  %s دو مدیر دارد: %s' % (group.name, '، '.join(names)))
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
