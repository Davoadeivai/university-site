"""نمایش «چقدر پر شده» در فهرست ادمین.

یک ستون که برای هر رکورد نوار پیشرفت و فهرست فیلدهای جامانده را نشان
می‌دهد. کافی است میکسین به ModelAdmin اضافه شود و `completeness` در
list_display بیاید.
"""
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from core.completeness import evaluate


class CompletenessAdminMixin:
    """ستون درصد تکمیل + هشدار فیلدهای حیاتی جامانده."""

    @staticmethod
    def _bar_color(percent: int) -> str:
        if percent >= 85:
            return '#0f7a5e'
        if percent >= 55:
            return '#c9922b'
        return '#b03a2e'

    def completeness(self, obj):
        data = evaluate(obj)
        percent = data['percent']
        if percent is None:
            return '—'

        color = self._bar_color(percent)
        missing = data['missing']
        critical = data['critical']

        if critical:
            hint = 'جا مانده (مهم): ' + '، '.join(critical[:6])
        elif missing:
            hint = 'جا مانده: ' + '، '.join(missing[:6])
        else:
            hint = 'همهٔ فیلدهای مهم پر است'

        return format_html(
            '<div title="{}" style="min-width:150px">'
            '  <div style="background:#e9eef5;border-radius:6px;height:8px;overflow:hidden">'
            '    <div style="width:{}%;height:100%;background:{}"></div>'
            '  </div>'
            '  <small style="color:{};font-weight:700">{}٪</small>'
            '  {}'
            '</div>',
            hint, percent, color, color, percent,
            mark_safe(
                '<small style="color:#b03a2e"> — %d فیلد مهم خالی</small>'
                % len(critical)
            ) if critical else '',
        )

    completeness.short_description = 'تکمیل صفحه'
