"""بارگذاری افراد و منابع موسسه از سند رسمی.

    python manage.py seed_directory

بی‌خطر است که چند بار اجرا شود: هر ردیف با کلید (دسته، نام) به‌روزرسانی
می‌شود، نه دوباره ساخته. عکس‌ها و هر فیلدی که ادمین دستی پر کرده باشد
دست نمی‌خورد — فقط فیلدهایی که در سند هستند بازنویسی می‌شوند.

با `--prune` ردیف‌هایی که دیگر در سند نیستند غیرفعال می‌شوند (پاک
نمی‌شوند، تا اگر عکسی برایشان آپلود شده بود از دست نرود).
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    BoardMember, PresidencyOffice, SecurityOffice, VicePresidency,
)
from directory.models import DirectoryPerson, ExternalResource

SEED_DIR = Path(__file__).resolve().parents[2] / 'seed_data'
DATA_FILE = SEED_DIR / 'people.json'
PHOTO_DIR = SEED_DIR / 'photos'

# دسته‌های افراد به‌ترتیبی که در سند آمده‌اند
PERSON_CATEGORIES = ('staff', 'founder', 'trustee', 'faculty', 'group_head', 'lecturer')

# نگاشت دستهٔ این اپ به `board_type` مدل قدیمی core.BoardMember که
# صفحه‌های «هیات موسس» و «هیات امنا» از آن می‌خوانند.
BOARD_TYPE_MAP = {'founder': 'founder', 'trustee': 'trustee'}

# عنوان‌هایی که ممکن است جلوی نام آمده باشند و نباید بخشی از کلید
# تطبیق باشند — وگرنه «دکتر احمدی» و «احمدی» دو نفر شمرده می‌شوند.
HONORIFICS = ('حجت‌الاسلام', 'حجت الاسلام', 'دکتر', 'مهندس', 'استاد', 'آقای', 'خانم')


# سمت کارمند در سند → نوع معاونت در core.VicePresidency.
# صفحهٔ «ریاست» و «معاونت‌ها» از آن مدل می‌خوانند، نه از این اپ، پس
# بدون این نگاشت عکس و نام معاونان هیچ‌وقت روی سایت دیده نمی‌شود.
VICE_BY_POSITION = {
    'معاون آموزشی و تحصیلات تکمیلی': 'education',
    'معاون دانشجویی و فرهنگی': 'student',
    'معاون اداری و مالی': 'admin_finance',
    'معاون پژوهش و فناوری': 'research',
    'معاون فنی و عمرانی': 'construction',
}

PRESIDENT_POSITION = 'رئیس موسسه'
SECURITY_POSITION = 'مسئول حراست'


def _is_placeholder(value: str) -> bool:
    """متن راهنمای جای‌خالی مثل «[نام را از پنل ادمین وارد کنید]».

    این‌ها را می‌شود بازنویسی کرد؛ متنی که آدم واقعاً نوشته نه.
    """
    text = (value or '').strip()
    return not text or (text.startswith('[') and text.endswith(']'))


def _bare_name(name: str) -> str:
    """نام بدون پیشوند افتخاری، برای تطبیق دو نوشتار از یک نفر."""
    cleaned = (name or '').strip()
    changed = True
    while changed:
        changed = False
        for title in HONORIFICS:
            if cleaned.startswith(title + ' '):
                cleaned = cleaned[len(title) + 1:].strip()
                changed = True
    return cleaned


def _match_key(name: str) -> str:
    """کلید مقایسه — فاصله و نیم‌فاصله و شکل حروف را نادیده می‌گیرد.

    «سید محمد سیدحسینی» و «سیدمحمد سیدحسینی» یک نفرند، ولی مقایسهٔ
    رشته‌ای آن‌ها را دو نفر می‌دید و دستور یک تعارض ساختگی گزارش
    می‌کرد: «در سایت … ولی در سند …» برای نامی که فقط یک فاصله فرق
    داشت. آن هشدار توجه را از دو تعارض واقعی برمی‌داشت.
    """
    cleaned = _bare_name(name)
    cleaned = cleaned.replace('ي', 'ی').replace('ك', 'ک')
    cleaned = cleaned.replace('‌', '').replace('‏', '')
    return ''.join(cleaned.split())


class Command(BaseCommand):
    help = 'بارگذاری افراد، هیات‌ها و منابع بیرونی از سند رسمی موسسه'

    def add_arguments(self, parser):
        parser.add_argument(
            '--prune', action='store_true',
            help='ردیف‌هایی که در سند نیستند را غیرفعال کن',
        )
        parser.add_argument(
            '--trust-document', action='store_true',
            help='وقتی نام ثبت‌شده با سند فرق دارد، سند را درست بگیر و '
                 'نام سایت را بازنویسی کن. این یک ادعای عمومی دربارهٔ '
                 'افراد نام‌برده است، پس عمداً پیش‌فرض نیست.',
        )
        parser.add_argument(
            '--refresh-photos', action='store_true',
            help='عکس‌ها را حتی اگر از قبل وجود دارند دوباره از سند بگذار. '
                 'هر عکسی که خودتان در ادمین آپلود کرده‌اید هم بازنویسی '
                 'می‌شود، پس فقط وقتی بزنید که سند عکس‌های بهتری دارد.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not DATA_FILE.exists():
            self.stderr.write('فایل داده پیدا نشد: %s' % DATA_FILE)
            return

        data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        created = updated = photos = 0
        seen: dict[str, set] = {c: set() for c in PERSON_CATEGORIES}

        for category in PERSON_CATEGORIES:
            for index, row in enumerate(data.get(category, []), start=1):
                full_name = row.get('full_name') or (
                    '%s %s' % (row.get('first_name', ''), row.get('last_name', ''))
                ).strip()
                if not full_name:
                    continue
                seen[category].add(full_name)

                obj, was_created = DirectoryPerson.objects.update_or_create(
                    category=category,
                    full_name=full_name,
                    defaults={
                        'honorific': row.get('honorific', ''),
                        'first_name': row.get('first_name', ''),
                        'last_name': row.get('last_name', ''),
                        'position': row.get('position', ''),
                        'field_of_study': row.get('field_of_study', ''),
                        'degree': row.get('degree', ''),
                        'extension': row.get('extension', ''),
                        'phone': row.get('phone', ''),
                        'email': row.get('email', ''),
                        'order': index,
                        'is_active': True,
                    },
                )
                created += was_created
                updated += not was_created
                photos += self._attach_photo(
                    obj, row.get('photo'), refresh=options['refresh_photos'])

            if options['prune']:
                stale = DirectoryPerson.objects.filter(
                    category=category, is_active=True,
                ).exclude(full_name__in=seen[category])
                count = stale.update(is_active=False)
                if count:
                    self.stdout.write('  %s: %d ردیف قدیمی غیرفعال شد' % (category, count))

        board_synced, board_merged = self._sync_board_members(data)
        lead_changed, conflicts = self._sync_leadership(
            data, refresh=options['refresh_photos'],
            trust_document=options['trust_document'])
        res_created, res_updated = self._sync_resources(data.get('resources', []))

        self.stdout.write(self.style.SUCCESS(
            'افراد: %d ساخته، %d به‌روز شد.' % (created, updated)))
        if photos:
            self.stdout.write(self.style.SUCCESS('تصویر: %d مورد ضمیمه شد.' % photos))
        self.stdout.write(self.style.SUCCESS(
            'اعضای هیات (صفحهٔ عمومی): %d ردیف همگام شد.' % board_synced))
        if board_merged:
            self.stdout.write(self.style.WARNING(
                '  %d ردیف تکراری هیات ادغام و حذف شد.' % board_merged))
        self.stdout.write(self.style.SUCCESS(
            'ریاست و معاونت‌ها: %d مورد پر شد.' % lead_changed))
        self.stdout.write(self.style.SUCCESS(
            'منابع بیرونی: %d ساخته، %d به‌روز شد.' % (res_created, res_updated)))

        if conflicts:
            if options['trust_document']:
                head = '\n%d نام با سند یکی نبود و به نفع سند عوض شد:'
                tail = ('اگر سند قدیمی است، نام درست را در پنل ادمین بگذارید '
                        'و دیگر --trust-document نزنید.')
            else:
                head = '\n%d مورد با سند نمی‌خواند — دست نخورد، خودتان تصمیم بگیرید:'
                tail = 'اگر سند درست است، نام را در پنل ادمین اصلاح کنید.'
            self.stdout.write(self.style.WARNING(head % len(conflicts)))
            for line in conflicts:
                self.stdout.write('  - %s' % line)
            self.stdout.write(tail)

    def _attach_photo(self, person, filename, refresh: bool = False,
                      field: str = 'photo') -> int:
        """تصویر سند را ضمیمه می‌کند.

        `field` وجود دارد چون این تابع روی چهار مدل با نام فیلد متفاوت
        کار می‌کند: `DirectoryPerson.photo`، `VicePresidency.photo`،
        `PresidencyOffice.president_photo` و `SecurityOffice.manager_photo`.

        به‌صورت پیش‌فرض فقط وقتی که تصویری وجود ندارد. دو دلیل: (۱) اگر
        ادمین عکس بهتری آپلود کرده، اجرای دوبارهٔ seed نباید رویش
        بنویسد؛ (۲) FileField در هر ذخیره نام تکراری را با پسوند عددی
        ذخیره می‌کند، پس بدون این شرط هر اجرا یک کپی تازه می‌ساخت.

        با `--refresh-photos` عکس قبلی از دیسک پاک و نسخهٔ سند
        جایگزین می‌شود — برای وقتی که سند تازه‌ای با کیفیت بهتر رسیده.
        """
        if not filename:
            return 0
        current = getattr(person, field, None)
        if current and not refresh:
            return 0
        source = PHOTO_DIR / filename
        if not source.exists():
            return 0
        if current:
            # بدون حذف، فایل قدیمی یتیم روی دیسک می‌ماند و سهمیهٔ
            # هاست را بی‌دلیل پر می‌کند. ولی نشدنِ حذف نباید کل کار را
            # بخواباند: یک فایل قفل‌شده فقط چند کیلوبایت هدر است،
            # درحالی‌که استثنا اینجا بارگذاری بقیهٔ افراد را قطع می‌کند.
            try:
                current.close()
            except (OSError, ValueError):
                pass
            try:
                current.delete(save=False)
            except OSError as exc:
                self.stderr.write(
                    '  عکس قبلی %s پاک نشد (%s) — نسخهٔ تازه جایگزین می‌شود.'
                    % (person, exc.__class__.__name__))
        getattr(person, field).save(
            filename, ContentFile(source.read_bytes()), save=True)
        return 1

    # ── ریاست و معاونت‌ها ────────────────────────────────────────────
    def _sync_leadership(self, data, refresh: bool,
                         trust_document: bool = False) -> tuple[int, list]:
        """نام و عکس رئیس، معاونان و مسئول حراست را سر جایشان می‌گذارد.

        صفحه‌های «ریاست»، «معاونت‌ها» و «حراست» از `PresidencyOffice`،
        `VicePresidency` و `SecurityOffice` می‌خوانند — نه از این اپ.
        بدون این بخش، عکس رئیس موسسه در سند بود ولی صفحهٔ ریاست
        همچنان عکس قدیمی را نشان می‌داد.

        متنی که کسی واقعاً نوشته بازنویسی نمی‌شود. اگر نام ثبت‌شده با
        سند فرق داشت، تغییرش نمی‌دهیم ولی در خروجی گزارش می‌شود تا
        تصمیمش با آدم باشد، نه با اسکریپت.

        وقتی نام تناقض دارد، عکس هم گذاشته نمی‌شود. عکسِ سند متعلق به
        آدمِ سند است؛ نشاندنش کنار نامی که با آن نمی‌خواند، بدتر از
        نبودِ عکس است — نام یک نفر با چهرهٔ نفر دیگر.
        """
        staff = {}
        for row in data.get('staff', []):
            position = (row.get('position') or '').strip()
            if position:
                staff[position] = row

        changed = 0
        conflicts: list[str] = []

        # ── رئیس موسسه ──
        row = staff.get(PRESIDENT_POSITION)
        if row:
            office = PresidencyOffice.objects.first() or PresidencyOffice()
            name = self._person_name(row)
            mismatch = False
            if _is_placeholder(office.president_name):
                office.president_name = name
                changed += 1
            elif _match_key(office.president_name) != _match_key(name):
                if trust_document:
                    conflicts.append(
                        'رئیس موسسه: «%s» با «%s» جایگزین شد'
                        % (office.president_name, name))
                    office.president_name = name
                    changed += 1
                else:
                    mismatch = True
                    conflicts.append(
                        'رئیس موسسه: در سایت «%s» ولی در سند «%s»'
                        % (office.president_name, name))
            if not office.president_phone and row.get('extension'):
                office.president_phone = 'داخلی %s' % row['extension']
            office.save()
            if not mismatch:
                changed += self._attach_photo(
                    office, row.get('photo'), refresh=refresh,
                    field='president_photo')

        # ── معاونان ──
        for position, vice_type in VICE_BY_POSITION.items():
            row = staff.get(position)
            if not row:
                continue
            vice, _created = VicePresidency.objects.get_or_create(
                vice_type=vice_type, defaults={'is_active': True})
            name = self._person_name(row)
            mismatch = False
            if _is_placeholder(vice.full_name):
                vice.full_name = name
                changed += 1
            elif _match_key(vice.full_name) != _match_key(name):
                if trust_document:
                    conflicts.append(
                        '%s: «%s» با «%s» جایگزین شد'
                        % (position, vice.full_name, name))
                    vice.full_name = name
                    changed += 1
                else:
                    mismatch = True
                    conflicts.append(
                        '%s: در سایت «%s» ولی در سند «%s»'
                        % (position, vice.full_name, name))
            if not vice.phone and row.get('extension'):
                vice.phone = 'داخلی %s' % row['extension']
            vice.save()
            if not mismatch:
                changed += self._attach_photo(
                    vice, row.get('photo'), refresh=refresh, field='photo')

        # ── حراست ──
        row = staff.get(SECURITY_POSITION)
        if row:
            security = SecurityOffice.objects.first()
            if security is not None:
                changed += self._attach_photo(
                    security, row.get('photo'), refresh=refresh,
                    field='manager_photo')

        return changed, conflicts

    @staticmethod
    def _person_name(row) -> str:
        bare = row.get('full_name') or (
            '%s %s' % (row.get('first_name', ''), row.get('last_name', ''))
        ).strip()
        return ('%s %s' % (row.get('honorific', ''), bare)).strip()

    def _sync_board_members(self, data) -> tuple[int, int]:
        """`core.BoardMember` را هم پر می‌کند.

        صفحه‌های «هیات موسس» و «هیات امنا» از آن مدل می‌خوانند. اگر
        فقط این اپ پر شود، آن دو صفحه خالی می‌مانند و کاربر سایت
        تفاوتی نمی‌بیند.

        تطبیق روی نامِ بدون پیشوند انجام می‌شود. نسخهٔ اول این دستور
        روی `full_name` کامل کلید می‌زد و چون «حجت‌الاسلام محمد حیدری
        قاسمی» با ردیف قبلیِ «محمد حیدری قاسمی» یکی شمرده نمی‌شد، هر
        اجرا یک ردیف تازه می‌ساخت — روی سرور ۲۸ ردیف به‌جای ۱۴. اینجا
        ردیف‌های هم‌نام پیدا و ادغام می‌شوند تا خودش را ترمیم کند.
        """
        synced = merged = 0
        for category, board_type in BOARD_TYPE_MAP.items():
            for index, row in enumerate(data.get(category, []), start=1):
                bare = row.get('full_name', '').strip()
                if not bare:
                    continue
                honorific = row.get('honorific', '').strip()
                display = ('%s %s' % (honorific, bare)).strip()

                matches = [
                    obj for obj in BoardMember.objects.filter(board_type=board_type)
                    if _match_key(obj.full_name) == _match_key(bare)
                ]

                if matches:
                    keep = matches[0]
                    for extra in matches[1:]:
                        extra.delete()
                        merged += 1
                    keep.full_name = display
                    keep.title = row.get('position', '')
                    keep.order = index
                    keep.is_active = True
                    keep.save()
                else:
                    BoardMember.objects.create(
                        board_type=board_type, full_name=display,
                        title=row.get('position', ''), order=index,
                        is_active=True,
                    )
                synced += 1
        return synced, merged

    def _sync_resources(self, rows) -> tuple[int, int]:
        created = updated = 0
        for index, row in enumerate(rows, start=1):
            _, was_created = ExternalResource.objects.update_or_create(
                url=row['url'],
                defaults={
                    'title': row['title'],
                    'category': row.get('category', 'other'),
                    'description': row.get('description', ''),
                    'icon': row.get('icon', 'fas fa-database'),
                    'order': index,
                    'is_active': True,
                },
            )
            created += was_created
            updated += not was_created
        return created, updated
