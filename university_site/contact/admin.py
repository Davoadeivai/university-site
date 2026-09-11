from django.contrib import admin, messages
from django.db import transaction

from core.admin_jalali import JalaliAdminMixin
from core.jalali import format_jalali_datetime
from .models import ContactMessage, Alumni


@admin.register(ContactMessage)
class ContactMessageAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['full_name', 'email', 'phone', 'subject', 'student_number',
                    'receipt_badge', 'status', 'replied_badge', 'created_jalali']
    list_filter = ['status', 'subject', 'created_at']
    list_editable = ['status']
    search_fields = ['full_name', 'email', 'message', 'reply', 'phone',
                     'student_number', 'national_id']
    readonly_fields = ['full_name', 'email', 'phone', 'national_id', 'subject',
                       'message', 'student_number', 'attachment_preview',
                       'ip_address', 'created_at_jalali_ro']
    fieldsets = (
        ('پیام', {'fields': ('full_name', 'email', 'phone', 'national_id', 'subject', 'message', 'ip_address', 'created_at_jalali_ro')}),
        ('فیش واریزی', {
            'fields': ('student_number', 'attachment_preview'),
            'description': (
                'این بخش وقتی پر است که دانشجو از فرم «تماس با ما» فیش '
                'واریزی فرستاده باشد. برای دیدن تصویر در اندازهٔ کامل، '
                'روی آن کلیک کنید.'
            ),
        }),
        ('پاسخ', {
            'fields': ('status', 'reply'),
            'description': (
                'با ذخیرهٔ متن پاسخ، همان متن <strong>واقعاً برای فرستنده ارسال می‌شود</strong> '
                '(پیامک به شمارهٔ تماس و ایمیل، هرکدام که ثبت شده باشد) و وضعیت به '
                '«پاسخ داده شده» تغییر می‌کند. تا زمانی که متن را عوض نکنید، ارسال تکرار نمی‌شود.'
            ),
        }),
    )

    @admin.display(description='پاسخ داده شده؟', boolean=True)
    def replied_badge(self, obj):
        return bool((obj.reply or '').strip())

    @admin.display(description='فیش', boolean=True)
    def receipt_badge(self, obj):
        return bool(obj.attachment)

    @admin.display(description='تصویر فیش')
    def attachment_preview(self, obj):
        """بندانگشتی، با پیوند به اندازهٔ کامل.

        فیش را باید خواند، نه فقط دید که هست: شمارهٔ پیگیری و مبلغ
        روی بندانگشتی خوانده نمی‌شود، پس تصویر به فایل اصلی پیوند
        می‌خورد.
        """
        from django.utils.html import format_html

        if not obj.attachment:
            return '—'
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener">'
            '<img src="{0}" style="max-width:320px;max-height:420px;'
            'border:1px solid #ddd;border-radius:6px"></a>',
            obj.attachment.url)

    @admin.display(description='تاریخ ثبت')
    def created_at_jalali_ro(self, obj):
        return format_jalali_datetime(obj.created_at)

    def save_model(self, request, obj, form, change):
        """پاسخ تازه را پس از commit واقعاً برای فرستنده می‌فرستد."""
        reply_changed = 'reply' in form.changed_data and (obj.reply or '').strip()

        if reply_changed and obj.status in ('new', 'read'):
            obj.status = 'replied'

        super().save_model(request, obj, form, change)

        if not reply_changed:
            return

        def _deliver():
            from core.notify import email_contact_reply, notify_contact_reply

            sent = []
            if notify_contact_reply(obj):
                sent.append('پیامک')
            if email_contact_reply(obj):
                sent.append('ایمیل')
            if sent:
                self.message_user(
                    request, f'پاسخ از طریق {" و ".join(sent)} ارسال شد.', messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    'پاسخ ذخیره شد اما ارسال نشد — شماره/ایمیل معتبر نبود یا سرویس پیامک خاموش است.',
                    messages.WARNING,
                )

        transaction.on_commit(_deliver)


@admin.register(Alumni)
class AlumniAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'graduation_year', 'major', 'degree', 'is_featured']
    list_filter = ['graduation_year', 'is_featured', 'degree']
    list_editable = ['is_featured']
    search_fields = ['full_name', 'major', 'success_story']
