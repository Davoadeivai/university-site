from django.contrib import admin, messages
from django.db import transaction

from core.admin_jalali import JalaliAdminMixin
from core.jalali import format_jalali_datetime
from .models import ContactMessage, Alumni


@admin.register(ContactMessage)
class ContactMessageAdmin(JalaliAdminMixin, admin.ModelAdmin):
    list_display = ['full_name', 'email', 'phone', 'subject', 'status', 'replied_badge', 'created_jalali']
    list_filter = ['status', 'subject', 'created_at']
    list_editable = ['status']
    search_fields = ['full_name', 'email', 'message', 'reply', 'phone']
    readonly_fields = ['full_name', 'email', 'phone', 'subject', 'message', 'ip_address', 'created_at_jalali_ro']
    fieldsets = (
        ('پیام', {'fields': ('full_name', 'email', 'phone', 'subject', 'message', 'ip_address', 'created_at_jalali_ro')}),
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
