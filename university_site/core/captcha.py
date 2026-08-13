"""کپچای حسابی — یک تصویر، یک پاسخ عددی.

چرا حساب و نه حروف درهم
───────────────────────
کپچای حرفی برای کاربر فارسی‌زبان یعنی خواندن حروف لاتینِ کج‌وکوله و
تایپ‌کردنشان با صفحه‌کلید فارسی. یک جمع دو رقمی همان کار را می‌کند
بدون آن دردسر: خواندنش برای آدم بی‌زحمت است و برای ربات همان‌قدر
سخت که هر تصویر دیگری.

چه چیزی نگه داشته می‌شود
────────────────────────
فقط پاسخ در نشست (session) می‌ماند، نه در فرم. اگر عدد در یک فیلد
مخفی می‌رفت، هر ربات ساده‌ای می‌خواندش. تصویر هم هر بار از نو کشیده
می‌شود، پس ذخیره‌سازی روی دیسک ندارد.

سه محافظ
────────
پنج دقیقه اعتبار، سه بار تلاش، و یک‌بارمصرف بودن. بدون آخری، یک
پاسخ درست را می‌شد بی‌نهایت بار در درخواست‌های پشت سر هم فرستاد.
"""
from __future__ import annotations

import io
import random
import time

SESSION_KEY = '_captcha'
TTL_SECONDS = 300
MAX_ATTEMPTS = 3

WIDTH, HEIGHT = 200, 68

# رنگ متن — تیره تا روی پس‌زمینهٔ روشن خوانا باشد، ولی نه یک‌دست
# مشکی که برداشتنش با آستانه‌گیری ساده شود.
INK = ((26, 58, 107), (16, 78, 66), (110, 36, 40), (62, 40, 100))
PAPER = (247, 248, 250)


def _pick() -> tuple[str, int]:
    """یک پرسش و پاسخش. عمداً بدون عدد منفی و بدون تقسیم."""
    op = random.choice('++-x')          # جمع کمی محتمل‌تر: خواناتر است
    if op == '+':
        a, b = random.randint(3, 19), random.randint(2, 19)
        return '%d + %d' % (a, b), a + b
    if op == '-':
        a = random.randint(8, 25)
        b = random.randint(2, a - 1)
        return '%d - %d' % (a, b), a - b
    a, b = random.randint(2, 9), random.randint(2, 9)
    return '%d x %d' % (a, b), a * b


def new_challenge(session) -> None:
    """پرسش تازه می‌سازد و در نشست می‌گذارد."""
    text, answer = _pick()
    session[SESSION_KEY] = {
        'text': text,
        'answer': str(answer),
        'born': time.time(),
        'tries': 0,
    }
    session.modified = True


def _state(session) -> dict | None:
    data = session.get(SESSION_KEY)
    if not isinstance(data, dict) or 'answer' not in data:
        return None
    if time.time() - data.get('born', 0) > TTL_SECONDS:
        session.pop(SESSION_KEY, None)
        return None
    return data


def render(session) -> bytes:
    """PNG پرسش فعلی. اگر پرسشی نباشد، یکی تازه ساخته می‌شود."""
    from PIL import Image, ImageDraw, ImageFont

    data = _state(session)
    if data is None:
        new_challenge(session)
        data = session[SESSION_KEY]

    image = Image.new('RGB', (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)

    # تار عنکبوت پس‌زمینه — قبل از متن، تا زیرش بیفتد
    for _ in range(5):
        draw.line(
            [(random.randint(0, WIDTH), random.randint(0, HEIGHT))
             for _ in range(3)],
            fill=(random.randint(170, 215),) * 3, width=1)
    for _ in range(220):
        draw.point((random.randint(0, WIDTH), random.randint(0, HEIGHT)),
                   fill=(random.randint(160, 220),) * 3)

    # Pillow ≥۱۰٫۱ یک فونت برداری داخلی دارد، پس فایل فونت لازم نیست.
    font_digit = ImageFont.load_default(size=38)
    # عملگر درشت‌تر کشیده می‌شود: یک خط تیرهٔ کوچک کنار خط‌های
    # اخلال‌گر گم می‌شود و «۱۵ - ۲» به «۱۵ ۲» تبدیل می‌شود.
    font_op = ImageFont.load_default(size=48)

    text = data['text']
    # هر نویسه جدا کشیده و کج می‌شود؛ کجیِ یک‌دستِ کل رشته را
    # می‌شود با یک چرخش برگرداند، کجیِ نویسه‌به‌نویسه را نه.
    glyphs = []
    for ch in text:
        is_op = ch in '+-x'
        font = font_op if is_op else font_digit
        box = font.getbbox(ch)
        w, h = max(box[2] - box[0], 1), max(box[3] - box[1], 1)
        tile = Image.new('RGBA', (w + 16, h + 16), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((8 - box[0], 8 - box[1]), ch,
                                  font=font, fill=random.choice(INK))
        # عملگر کمتر کج می‌شود تا با خط‌های پس‌زمینه اشتباه نشود
        spin = random.uniform(-8, 8) if is_op else random.uniform(-20, 20)
        tile = tile.rotate(spin, resample=Image.BICUBIC, expand=True)
        glyphs.append(tile)

    total = sum(g.width for g in glyphs) - 6 * (len(glyphs) - 1)
    x = max((WIDTH - total) // 2, 2)
    for tile in glyphs:
        y = (HEIGHT - tile.height) // 2 + random.randint(-5, 5)
        image.paste(tile, (x, y), tile)
        x += tile.width - 6            # کمی هم‌پوشانی: جداکردن را سخت می‌کند

    # یک خط روی متن، و عمداً موج‌دار. خط صافِ افقی از دور شبیه علامت
    # منها می‌شود و «۱۰ + ۶» را به «۱۰ - ۶» تبدیل می‌کند.
    y = random.randint(16, HEIGHT - 16)
    draw.line([(0, y + random.randint(-10, 10)),
               (WIDTH // 3, y + random.randint(-16, 16)),
               (2 * WIDTH // 3, y + random.randint(-16, 16)),
               (WIDTH, y + random.randint(-10, 10))],
              fill=random.choice(INK), width=2, joint='curve')

    buffer = io.BytesIO()
    image.save(buffer, 'PNG')
    return buffer.getvalue()


def check(session, raw: str) -> bool:
    """درست بود یا نه. در هر دو حالت پرسش مصرف می‌شود."""
    from core.iran import only_digits

    data = _state(session)
    if data is None:
        return False

    data['tries'] = data.get('tries', 0) + 1
    session[SESSION_KEY] = data
    session.modified = True

    given = only_digits(raw or '')
    if given and given == data['answer']:
        session.pop(SESSION_KEY, None)   # یک‌بارمصرف
        session.modified = True
        return True

    if data['tries'] >= MAX_ATTEMPTS:
        session.pop(SESSION_KEY, None)
        session.modified = True
    return False


def is_enabled() -> bool:
    from django.conf import settings
    return getattr(settings, 'CAPTCHA_ENABLED', True)
