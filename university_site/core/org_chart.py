"""راهنمای متنیِ چارت سازمانی.

چرا لازم است
────────────
چارت رسمی موسسه یک تصویر است و همان روی صفحه می‌نشیند. ولی تصویر
سه کار را نمی‌کند:

  ۱. روی موبایل خوانده نمی‌شود — نوشته‌هایش برای کاغذ A4 ساخته شده،
     نه برای نمایشگر شش‌اینچی.
  ۲. جست‌وجو نمی‌شود — نه با Ctrl+F مرورگر، نه با جست‌وجوی خود سایت،
     نه با گوگل. کسی که دنبال «ادارهٔ امتحانات» است آن را پیدا نمی‌کند.
  ۳. کلیک نمی‌شود — واحدی که صفحهٔ خودش را دارد، از چارت به آن راه
     ندارد. و صفحه‌خوان چیزی جز «چارت سازمانی» نمی‌خواند.

این فهرست همان ساختار را در متن می‌گذارد؛ زیر تصویر، نه به‌جایش.

از کجا خوانده می‌شود
────────────────────
معاونت‌ها و زیرمجموعه‌هایشان از `core.vices` می‌آیند — همان منبعی
که نوار بالای سایت از آن می‌خواند و آزمون‌ها آن را با خودِ تصویرِ
چارت تطبیق می‌دهند. پس اگر چارت عوض شود، یک جا اصلاح می‌شود و هر سه
(منو، صفحهٔ معاونت‌ها، و این فهرست) با هم به‌روز می‌شوند.

بالای چارت — ارکان و حوزهٔ ریاست — اینجا نوشته شده، چون جای دیگری
به‌شکل درخت وجود ندارد.
"""
from __future__ import annotations

from django.urls import NoReverseMatch, reverse

# (عنوان، نام مسیر، زیرمجموعه‌ها) — دقیقاً به ترتیب چارت رسمی
TOP = [
    ('هیئت مؤسس', 'core:board_founders', []),
    ('هیئت امنا', 'core:board_trustees', []),
    ('شورای مؤسسه', 'core:councils', []),
    ('رئیس مؤسسه', 'core:presidency', [
        ('قائم مقام', '', []),
        ('دفتر ریاست و روابط عمومی', 'core:public_relations', []),
        ('حراست', 'core:security_office', []),
        ('دفتر حقوقی', '', []),
        ('دفتر نظارت و ارزیابی', '', []),
    ]),
]


def _url(name: str) -> str:
    """نشانی یک مسیر نام‌دار؛ نبودنش نباید کل صفحه را بیندازد."""
    if not name:
        return ''
    try:
        return reverse(name)
    except NoReverseMatch:
        return ''


def _rows(spec) -> list:
    return [{'title': title, 'url': _url(name), 'children': _rows(kids)}
            for title, name, kids in spec]


def build(vice_rows=None) -> list:
    """ارکان و حوزهٔ ریاست، و پس از آن پنج معاونت با زیرمجموعه‌هایشان."""
    from core import vices

    rows = _rows(TOP)
    if vice_rows is None:
        vice_rows = vices.build()
    for vice in vice_rows:
        rows.append({
            'title': vice['label'],
            'url': vice['url'],
            'children': vice['children'],
        })
    return rows


def count(rows=None) -> int:
    """شمار واحدها — برای اینکه فهرست بگوید چقدر است، پیش از بازشدن."""
    if rows is None:
        rows = build()
    return sum(1 + count(row['children']) for row in rows)
