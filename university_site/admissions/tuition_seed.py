"""پر کردن ساختار شهریه برای رشته‌های فعال که هنوز شهریه ندارند."""
from __future__ import annotations

from django.db.models import Count

from academics.models import Major
from admissions.models import TuitionStructure


_DEFAULT_FEES = {
    'fixed_fee': 5_000_000,
    'theory_fee': 450_000,
    'practical_fee': 550_000,
    'lab_fee': 600_000,
    'registration_fee': 200_000,
    'insurance_fee': 0,
    'card_fee': 0,
    'dorm_fee': 0,
}


def _template_fees_and_year():
    year_row = (
        TuitionStructure.objects.filter(is_active=True)
        .values('academic_year')
        .annotate(n=Count('id'))
        .order_by('-n', '-academic_year')
        .first()
    )
    academic_year = (year_row or {}).get('academic_year') or '1404-1405'
    sample = (
        TuitionStructure.objects.filter(is_active=True, academic_year=academic_year)
        .order_by('id')
        .first()
    )
    if sample is None:
        sample = TuitionStructure.objects.filter(is_active=True).order_by('-academic_year', 'id').first()
    if sample is None:
        return academic_year, dict(_DEFAULT_FEES)

    return academic_year, {
        'fixed_fee': sample.fixed_fee,
        'theory_fee': sample.theory_fee,
        'practical_fee': sample.practical_fee,
        'lab_fee': sample.lab_fee,
        'registration_fee': sample.registration_fee,
        'insurance_fee': sample.insurance_fee,
        'card_fee': sample.card_fee,
        'dorm_fee': sample.dorm_fee,
    }


def ensure_tuition_structures_for_active_majors() -> dict:
    """
    برای هر رشته فعال بدون ساختار شهریهٔ فعال، یک رکورد می‌سازد.
    مبالغ از الگوی موجود کپی می‌شود تا ادمین در پنل ویرایش کند.
    """
    academic_year, fees = _template_fees_and_year()
    created = 0
    reactivated = 0
    skipped = 0

    majors = Major.objects.filter(is_active=True).order_by('degree', 'name')
    for major in majors:
        if TuitionStructure.objects.filter(major=major, is_active=True).exists():
            skipped += 1
            continue

        inactive = (
            TuitionStructure.objects.filter(major=major, is_active=False)
            .order_by('-academic_year')
            .first()
        )
        if inactive:
            inactive.is_active = True
            inactive.save(update_fields=['is_active'])
            reactivated += 1
            continue

        _, was_created = TuitionStructure.objects.get_or_create(
            major=major,
            academic_year=academic_year,
            defaults={
                **fees,
                'is_active': True,
                'notes': 'ایجاد خودکار برای نمایش در محاسبه‌گر؛ لطفاً مبالغ را در پنل ادمین بررسی کنید.',
            },
        )
        if was_created:
            created += 1
        else:
            ts = TuitionStructure.objects.get(major=major, academic_year=academic_year)
            if not ts.is_active:
                ts.is_active = True
                ts.save(update_fields=['is_active'])
                reactivated += 1
            else:
                skipped += 1

    return {
        'academic_year': academic_year,
        'created': created,
        'reactivated': reactivated,
        'skipped': skipped,
    }


def needs_tuition_seed() -> bool:
    return Major.objects.filter(is_active=True).exclude(
        tuition_structures__is_active=True
    ).exists()
