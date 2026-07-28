"""گزارش مالی یکپارچه — پرداخت‌های پذیرش و داشبورد در یک نما.

پرداخت‌ها در پروژه بین دو مدل پخش‌اند:

* ``admissions.StudentPayment`` — اقساط شهریهٔ متقاضی، پیش از ساخت حساب کاربری
* ``dashboard.Payment``        — پرداخت‌های دانشجوی ثبت‌نام‌شده (درگاه/آفلاین)

تا پیش از این برای دیدن وضعیت مالی یک نفر باید هر دو لیست جداگانه باز می‌شد.
این ویو فقط‌خواندنی هر دو را نرمال‌سازی و کنار هم نمایش می‌دهد.
"""
from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_GET

from core.jalali import format_jalali_date, format_jalali_datetime


def _safe_url(viewname, *args):
    try:
        return reverse(viewname, args=args)
    except NoReverseMatch:
        return ''


def _admission_rows(status: str, q: str):
    from admissions.models import StudentPayment

    qs = StudentPayment.objects.select_related('application').order_by('-due_date')
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(application__national_id__icontains=q) | qs.filter(
            application__last_name__icontains=q
        )

    rows = []
    for p in qs[:400]:
        app = p.application
        rows.append({
            'source': 'پذیرش',
            'person': f'{app.first_name} {app.last_name}'.strip() if app else '—',
            'national_id': getattr(app, 'national_id', '') or '',
            'title': f'قسط {p.installment_no}',
            'amount': int(p.amount or 0),
            'status': p.get_status_display(),
            'status_key': p.status,
            'due': format_jalali_date(p.due_date, 'short') if p.due_date else '—',
            'paid': format_jalali_datetime(p.paid_at) if p.paid_at else '—',
            'method': '—',
            'url': _safe_url('admin:admissions_studentpayment_change', p.pk),
        })
    return rows


def _dashboard_rows(status: str, q: str):
    from dashboard.models import Payment

    qs = Payment.objects.select_related('student', 'semester').order_by('-due_date')
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(student__username__icontains=q) | qs.filter(
            student__last_name__icontains=q
        )

    rows = []
    for p in qs[:400]:
        user = p.student
        name = (user.get_full_name() or user.username) if user else '—'
        try:
            title = p.get_installment_stage_display() or p.get_payment_type_display()
        except Exception:
            title = p.payment_type or 'پرداخت'
        try:
            method = p.get_method_display()
        except Exception:
            method = p.method or '—'
        rows.append({
            'source': 'داشبورد',
            'person': name,
            'national_id': getattr(user, 'username', '') or '',
            'title': title,
            'amount': int(p.amount or 0),
            'status': p.get_status_display(),
            'status_key': p.status,
            'due': format_jalali_date(p.due_date, 'short') if p.due_date else '—',
            'paid': format_jalali_datetime(p.payment_date) if p.payment_date else '—',
            'method': method,
            'url': _safe_url('admin:dashboard_payment_change', p.pk),
        })
    return rows


@staff_member_required
@require_GET
def finance_overview(request):
    """نمای مالی یکپارچه. نیازمند مجوز مشاهدهٔ هر دو مدل پرداخت."""
    if not (
        request.user.has_perm('dashboard.view_payment')
        or request.user.has_perm('admissions.view_studentpayment')
    ):
        raise PermissionDenied

    status = (request.GET.get('status') or '').strip()
    source = (request.GET.get('source') or '').strip()
    q = (request.GET.get('q') or '').strip()

    rows = []
    if source in ('', 'admissions') and request.user.has_perm('admissions.view_studentpayment'):
        rows += _admission_rows(status, q)
    if source in ('', 'dashboard') and request.user.has_perm('dashboard.view_payment'):
        rows += _dashboard_rows(status, q)

    rows.sort(key=lambda r: (r['status_key'] != 'review', r['person']))

    paid_total = sum(r['amount'] for r in rows if r['status_key'] == 'paid')
    pending_total = sum(r['amount'] for r in rows if r['status_key'] in ('pending', 'review'))
    overdue_total = sum(r['amount'] for r in rows if r['status_key'] == 'overdue')

    from django.contrib import admin as dj_admin

    ctx = {
        **dj_admin.site.each_context(request),
        'title': 'گزارش مالی یکپارچه',
        'rows': rows,
        'row_count': len(rows),
        'truncated': len(rows) >= 800,
        'summary': {
            'paid': paid_total,
            'pending': pending_total,
            'overdue': overdue_total,
            'grand': paid_total + pending_total + overdue_total,
        },
        'cur_status': status,
        'cur_source': source,
        'cur_q': q,
        'status_choices': [
            ('', 'همه وضعیت‌ها'),
            ('review', 'منتظر تأیید'),
            ('pending', 'در انتظار پرداخت'),
            ('paid', 'پرداخت‌شده'),
            ('overdue', 'معوق'),
        ],
    }
    return render(request, 'admin/core/finance_overview.html', ctx)
