"""هاب یکپارچه مسیر دانشجو: مقطع/رشته → پذیرش → شهریه → ترم → تسویه."""
from __future__ import annotations

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from academics.models import Major
from core.degree_map import (
    HUB_DEGREE_FILTERS,
    admission_degree_for_major,
    document_degree_for_major,
    document_degree_for_query,
    hub_degree_label,
    major_degree_q,
    normalize_degree_query,
)


WIZARD_STEPS = [
    {'num': 1, 'key': 'major', 'title': 'مقطع و رشته'},
    {'num': 2, 'key': 'details', 'title': 'جزئیات و شهریه'},
    {'num': 3, 'key': 'apply', 'title': 'ثبت درخواست'},
    {'num': 4, 'key': 'account', 'title': 'حساب و شهریه'},
    {'num': 5, 'key': 'term', 'title': 'انتخاب واحد'},
    {'num': 6, 'key': 'finish', 'title': 'پایان مسیر'},
]


def _parse_step(raw) -> int:
    try:
        step = int(raw or 1)
    except (TypeError, ValueError):
        step = 1
    return max(1, min(step, 6))


def student_path(request):
    """ویزارد مسیر دانشجو — نقطهٔ ورود یکپارچه."""
    step = _parse_step(request.GET.get('step'))
    degree = normalize_degree_query(request.GET.get('degree', ''))
    major_id = (request.GET.get('major') or request.GET.get('major_id') or '').strip()
    selected_major = None
    if major_id.isdigit():
        selected_major = (
            Major.objects.filter(pk=int(major_id), is_active=True)
            .select_related('group', 'department')
            .first()
        )
        if selected_major and not degree:
            degree = selected_major.admission_degree or selected_major.degree

    majors_qs = (
        Major.objects.filter(is_active=True)
        .select_related('group', 'department')
        .order_by('degree', 'group__order', 'order', 'name')
    )
    if degree:
        majors_qs = majors_qs.filter(major_degree_q(degree))

    # حذف تکراری هم‌نام در همان مقطع
    seen = set()
    majors = []
    for m in majors_qs:
        key = (m.degree, m.name.replace('\u200c', '').strip())
        if key in seen:
            continue
        seen.add(key)
        majors.append(m)

    user = request.user if request.user.is_authenticated else None
    journey = None
    academic_status = None
    terminal = False
    if user:
        try:
            from dashboard.onboarding import build_journey_status
            journey = build_journey_status(user=user)
            profile = getattr(user, 'profile', None)
            if profile:
                academic_status = profile.academic_status
                terminal = academic_status in ('graduated', 'withdrawn', 'expelled')
        except Exception:
            journey = None

    doc_degree = ''
    apply_degree = degree
    if selected_major:
        doc_degree = document_degree_for_major(selected_major.degree)
        apply_degree = admission_degree_for_major(selected_major)
    elif degree:
        from core.degree_map import to_canonical_degree
        apply_degree = to_canonical_degree(degree) or degree
        doc_degree = document_degree_for_query(apply_degree)

    apply_url = reverse('admissions:apply_otp_send')
    if apply_degree or selected_major:
        from urllib.parse import urlencode
        q = {}
        if apply_degree:
            q['degree'] = apply_degree
        if selected_major:
            q['major'] = selected_major.pk
        # پس از OTP به apply با همین پارامترها برویم
        apply_url = reverse('admissions:apply_otp_send') + '?' + urlencode(q)

    tuition_url = reverse('admissions:tuition_calc')
    if selected_major:
        from urllib.parse import urlencode
        tuition_url += '?' + urlencode({'major_id': selected_major.pk})

    docs_url = reverse('core:documents')
    if doc_degree:
        from urllib.parse import urlencode
        docs_url += '?' + urlencode({'degree': doc_degree})

    # گام بعدی پیشنهادی
    next_cta = None
    if terminal:
        next_cta = {
            'label': 'مشاهده وضعیت تحصیلی',
            'url': reverse('dashboard:dashboard'),
            'hint': 'حساب شما در وضعیت پایان‌تحصیل است؛ ثبت‌نام ترم جدید فعال نیست.',
        }
    elif step == 1 and not selected_major:
        next_cta = {'label': 'یک رشته انتخاب کنید', 'url': None, 'hint': 'روی کارت رشته کلیک کنید.'}
    elif step <= 2 and selected_major:
        next_cta = {
            'label': 'ادامه: جزئیات و شهریه',
            'url': reverse('core:student_path') + f'?step=2&major={selected_major.pk}',
            'hint': selected_major.name,
        }
    elif step == 3 or (step <= 3 and selected_major and not (user and journey and journey.get('application'))):
        next_cta = {
            'label': 'ثبت درخواست پذیرش',
            'url': apply_url,
            'hint': 'با تأیید موبایل فرم پذیرش را تکمیل کنید.',
        }
    elif journey and journey.get('next_url'):
        labels = {
            'account': 'ساخت / ورود به حساب',
            'tuition': 'پرداخت قسط اول شهریه',
            'registration': 'انتخاب واحد',
            'schedule': 'برنامه کلاس',
            'exam_card': 'کارت امتحان',
            'clearance': 'پیگیری تسویه',
            'lifecycle': 'درخواست فارغ‌التحصیلی / انصراف',
        }
        next_cta = {
            'label': labels.get(journey.get('next_key'), 'ادامه مسیر'),
            'url': journey['next_url'],
            'hint': '',
        }
    else:
        next_cta = {
            'label': 'ورود به پنل دانشجو',
            'url': reverse('accounts:login'),
            'hint': 'پس از پذیرش وارد حساب شوید.',
        }

    context = {
        'page_title': 'مسیر دانشجو',
        'wizard_steps': WIZARD_STEPS,
        'current_step': step,
        'degree': degree,
        'degree_label': hub_degree_label(degree),
        'degree_filters': HUB_DEGREE_FILTERS,
        'majors': majors,
        'selected_major': selected_major,
        'apply_url': apply_url,
        'tuition_url': tuition_url,
        'docs_url': docs_url,
        'journey': journey,
        'academic_status': academic_status,
        'terminal_status': terminal,
        'next_cta': next_cta,
        'apply_degree': apply_degree,
    }
    return render(request, 'core/student_path.html', context)


def student_path_select_major(request, slug):
    """انتخاب رشته و هدایت به مرحله ۲."""
    major = get_object_or_404(Major, slug=slug, is_active=True)
    url = reverse('core:student_path') + f'?step=2&major={major.pk}&degree={major.admission_degree}'
    return redirect(url)
