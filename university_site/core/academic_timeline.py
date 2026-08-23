"""تایم‌لاین تقویم آموزشی با وضعیت زندهٔ هر مرحله.

مدل AcademicCalendar از قبل وجود داشت ولی در صفحهٔ اصلی فقط یک لیست
ساده رندر می‌شد. اینجا هر مرحله وضعیت می‌گیرد — گذشته / جاری / بعدی —
و برای مرحلهٔ بعدی روزهای باقیمانده محاسبه می‌شود. همین وضعیت است که
یک تصویر ثابت نمی‌تواند بدهد.
"""
from __future__ import annotations

from django.utils import timezone


def build_timeline(limit: int = 8) -> dict:
    """مراحل نیمسال جاری با وضعیت. اگر داده‌ای نباشد dict خالی برمی‌گردد."""
    from academics.models import AcademicCalendar

    today = timezone.localdate()

    items = list(
        AcademicCalendar.objects.filter(is_active=True)
        .order_by('order', 'start_date')
    )
    if not items:
        return {'nodes': [], 'academic_year': '', 'has_data': False}

    # نیمسالی که امروز داخلش است، وگرنه نزدیک‌ترین نیمسال آینده،
    # وگرنه آخرین نیمسال ثبت‌شده
    years = {}
    for it in items:
        years.setdefault(it.academic_year or '', []).append(it)

    chosen_year, chosen = '', []
    for year, group in years.items():
        first = min(g.start_date for g in group)
        last = max((g.end_date or g.start_date) for g in group)
        if first <= today <= last:
            chosen_year, chosen = year, group
            break
    if not chosen:
        future = [(min(g.start_date for g in grp), y, grp)
                  for y, grp in years.items()
                  if min(g.start_date for g in grp) > today]
        if future:
            future.sort()
            _, chosen_year, chosen = future[0]
        else:
            past = [(max((g.end_date or g.start_date) for g in grp), y, grp)
                    for y, grp in years.items()]
            past.sort(reverse=True)
            _, chosen_year, chosen = past[0]

    chosen = sorted(chosen, key=lambda x: (x.order, x.start_date))[:limit]

    # اولین مرحله‌ای که هنوز تمام نشده = «بعدی»؛ اگر امروز داخلش باشد = «جاری»
    nodes = []
    next_marked = False
    for it in chosen:
        end = it.end_date or it.start_date
        if end < today:
            state = 'past'
        elif it.start_date <= today <= end:
            state = 'now'
        elif not next_marked:
            state = 'next'
            next_marked = True
        else:
            state = 'future'

        days_left = (it.start_date - today).days if state == 'next' else None

        nodes.append({
            'obj': it,
            'title': it.title,
            'description': it.description,
            'start': it.start_date,
            'end': it.end_date,
            'is_multi_day': it.is_multi_day,
            'state': state,
            'is_past': state == 'past',
            'is_now': state == 'now',
            'is_next': state == 'next',
            'days_left': days_left,
            'is_important': it.is_important,
            # نمایش و لینک — همه از پنل ادمین قابل تنظیم‌اند
            'url': it.get_action_url(),
            'action_label': it.get_action_display() if it.action else '',
            'icon': it.display_icon,
            'tone': it.tone or 'gold',
            # رنگ دلخواه زمینه؛ خالی یعنی همان رنگ‌بندی tone
            'card_style': it.card_style,
            'image': it.image if it.image else None,
        })

    return {
        'nodes': nodes,
        'academic_year': chosen_year,
        'has_data': True,
    }
