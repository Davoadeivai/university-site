"""متن بلندتر از ستون، پیش از ذخیره کوتاه می‌شود — نه خطای ۵۰۰.

مشکل
────
بیشتر فرم‌های عمومی (پذیرش، تماس، پروفایل، کتابخانه) مقدار را مستقیم
از \u200Erequest.POST\u200E برمی‌دارند و \u200Esave()\u200E می‌زنند، بی‌آنکه طولش را با
\u200Emax_length\u200E بسنجند. روی SQLite مهم نیست، ولی سرور MySQL با
\u200ESTRICT_TRANS_TABLES\u200E است: شماره‌تلفنی مثل «۰۹۱۲ ۳۴۵ ۶۷۸۹ (منزل)» در
ستون ۱۵ کاراکتری یعنی \u200EDataError\u200E و صفحهٔ خطای سرور برای کاربر.

راه‌حل
──────
یک \u200Epre_save\u200E سراسری: هر CharField که مقدار رشته‌ای بلندتر از سقفش
دارد بریده می‌شود و در لاگ هشدار می‌ماند تا فرمِ مقصر پیدا شود.
"""
from __future__ import annotations

import logging

from django.db import models
from django.db.models.signals import pre_save

logger = logging.getLogger('django')


def clip_char_fields(sender, instance, raw=False, **kwargs):
    if raw:  # loaddata
        return
    for field in sender._meta.concrete_fields:
        if not isinstance(field, models.CharField) or not field.max_length:
            continue
        value = getattr(instance, field.attname, None)
        if isinstance(value, str) and len(value) > field.max_length:
            logger.warning(
                'clipped %s.%s from %d to %d chars',
                sender.__name__, field.name, len(value), field.max_length)
            setattr(instance, field.attname, value[:field.max_length])


def register():
    pre_save.connect(clip_char_fields, dispatch_uid='core.clip_char_fields')
