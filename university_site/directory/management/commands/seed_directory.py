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

from core.models import BoardMember
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


class Command(BaseCommand):
    help = 'بارگذاری افراد، هیات‌ها و منابع بیرونی از سند رسمی موسسه'

    def add_arguments(self, parser):
        parser.add_argument(
            '--prune', action='store_true',
            help='ردیف‌هایی که در سند نیستند را غیرفعال کن',
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
                photos += self._attach_photo(obj, row.get('photo'))

            if options['prune']:
                stale = DirectoryPerson.objects.filter(
                    category=category, is_active=True,
                ).exclude(full_name__in=seen[category])
                count = stale.update(is_active=False)
                if count:
                    self.stdout.write('  %s: %d ردیف قدیمی غیرفعال شد' % (category, count))

        board_synced, board_merged = self._sync_board_members(data)
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
            'منابع بیرونی: %d ساخته، %d به‌روز شد.' % (res_created, res_updated)))

    def _attach_photo(self, person, filename) -> int:
        """تصویر سند را فقط وقتی ضمیمه می‌کند که فرد تصویری نداشته باشد.

        دو دلیل: (۱) اگر ادمین عکس بهتری آپلود کرده، اجرای دوبارهٔ seed
        نباید رویش بنویسد؛ (۲) FileField در هر ذخیره نام تکراری را با
        پسوند عددی ذخیره می‌کند، پس بدون این شرط هر اجرا یک کپی تازه
        روی دیسک می‌ساخت.
        """
        if not filename or person.photo:
            return 0
        source = PHOTO_DIR / filename
        if not source.exists():
            return 0
        person.photo.save(filename, ContentFile(source.read_bytes()), save=True)
        return 1

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
                    if _bare_name(obj.full_name) == bare
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
