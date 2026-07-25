"""لینک ورود یک‌بارمصرف با امضای زمانی Django."""
from __future__ import annotations

import hashlib

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

_SALT = 'aab-magic-login-v1'
_MAX_AGE = 30 * 60  # ۳۰ دقیقه


def _signer() -> TimestampSigner:
    return TimestampSigner(salt=_SALT)


def make_magic_token(user: User) -> str:
    return _signer().sign(str(user.pk))


def _used_key(token: str) -> str:
    digest = hashlib.sha256(token.encode('utf-8')).hexdigest()[:32]
    return f'magic:used:{digest}'


def consume_magic_token(token: str) -> User | None:
    """توکن را یک‌بار مصرف می‌کند؛ در صورت نامعتبر None."""
    if not token:
        return None
    key = _used_key(token)
    if cache.get(key):
        return None
    try:
        user_id = int(_signer().unsign(token, max_age=_MAX_AGE))
    except (BadSignature, SignatureExpired, ValueError, TypeError):
        return None
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if not user:
        return None
    cache.set(key, 1, timeout=_MAX_AGE)
    return user
