"""کارت تماس دفتر ریاست به شکل vCard.

چرا
───
شمارهٔ دفتر ریاست روی صفحه هست، ولی کسی که با گوشی می‌بیندش باید
آن را دستی در مخاطبان بنویسد — و شمارهٔ ۱۱ رقمی را غلط می‌نویسد.
یک فایل ‎.vcf‎ با یک ضربه در دفترچهٔ تلفن می‌نشیند.

قالب vCard 3.0 انتخاب شد چون هم اندروید و هم iOS بدون واسطه بازش
می‌کنند؛ نسخهٔ ۴ روی گوشی‌های قدیمی‌تر باز نمی‌شود.
"""
from __future__ import annotations

BACKSLASH = chr(92)


def _esc(value: str) -> str:
    """کاما و سمی‌کالن در vCard جداکنندهٔ فیلدند و باید فرار داده شوند.

    ترتیب مهم است: اول خودِ بک‌اسلش، وگرنه بک‌اسلش‌هایی که خودمان
    اضافه می‌کنیم دوباره فرار داده می‌شوند.
    """
    text = str(value or '')
    text = text.replace(BACKSLASH, BACKSLASH * 2)
    text = text.replace(';', BACKSLASH + ';')
    text = text.replace(',', BACKSLASH + ',')
    text = text.replace('\n', BACKSLASH + 'n')
    return text


def build(office, org: str = '') -> str:
    """متن vCard رئیس و دفتر ریاست."""
    name = (getattr(office, 'president_name', '') or '').strip()
    lines = ['BEGIN:VCARD', 'VERSION:3.0']

    if name:
        parts = name.split()
        family = parts[-1] if len(parts) > 1 else ''
        given = ' '.join(parts[:-1]) if len(parts) > 1 else name
        lines.append('N:%s;%s;;;' % (_esc(family), _esc(given)))
        lines.append('FN:%s' % _esc(name))

    if org:
        lines.append('ORG:%s' % _esc(org))
    title = (getattr(office, 'president_title', '') or '').strip()
    if title:
        lines.append('TITLE:%s' % _esc(title))

    for field, tag in (
        ('president_phone', 'TEL;TYPE=WORK,VOICE:'),
        ('office_phone', 'TEL;TYPE=WORK:'),
        ('office_fax', 'TEL;TYPE=FAX:'),
        ('president_email', 'EMAIL;TYPE=INTERNET:'),
        ('office_email', 'EMAIL;TYPE=INTERNET:'),
    ):
        value = (getattr(office, field, '') or '').strip()
        if value:
            lines.append('%s%s' % (tag, _esc(value)))

    site = (getattr(office, 'president_website', '') or '').strip()
    if site:
        lines.append('URL:%s' % _esc(site))

    address = (getattr(office, 'office_address', '') or '').strip()
    if address:
        lines.append('ADR;TYPE=WORK:;;%s;;;;' % _esc(address.replace('\n', ' ')))

    lines.append('END:VCARD')
    # vCard رسماً CRLF می‌خواهد؛ با \n تنها بعضی گوشی‌ها فایل را رد می‌کنند.
    return '\r\n'.join(lines) + '\r\n'
