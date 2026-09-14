import base64
import io
import random
import string
import uuid
from django.core.cache import cache
from PIL import Image, ImageDraw, ImageFont

CAPTCHA_TTL = 300
SMS_TTL = 300
CAPTCHA_PREFIX = "captcha:"
SMS_PREFIX = "sms:"
SMS_COOLDOWN_PREFIX = "sms_cd:"


def _random_text(length=4):
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    return "".join(random.choice(chars) for _ in range(length))


def _draw_captcha(text):
    width, height = 130, 46
    image = Image.new("RGB", (width, height), (245, 248, 252))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()

    for _ in range(6):
        draw.line(
            (
                random.randint(0, width),
                random.randint(0, height),
                random.randint(0, width),
                random.randint(0, height),
            ),
            fill=(
                random.randint(160, 210),
                random.randint(170, 220),
                random.randint(190, 235),
            ),
            width=1,
        )

    for i, ch in enumerate(text):
        color = (
            random.randint(20, 90),
            random.randint(40, 120),
            random.randint(140, 220),
        )
        draw.text((12 + i * 28, random.randint(4, 12)), ch, font=font, fill=color)

    for _ in range(40):
        draw.point(
            (random.randint(0, width - 1), random.randint(0, height - 1)),
            fill=(random.randint(100, 180), random.randint(100, 180), random.randint(100, 180)),
        )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def create_captcha():
    captcha_id = uuid.uuid4().hex
    text = _random_text(4)
    cache.set(f"{CAPTCHA_PREFIX}{captcha_id}", text.lower(), CAPTCHA_TTL)
    return {
        "captcha_id": captcha_id,
        "image": f"data:image/png;base64,{_draw_captcha(text)}",
        "expires_in": CAPTCHA_TTL,
    }


def verify_captcha(captcha_id, captcha_code, *, consume=True):
    if not captcha_id or not captcha_code:
        return False
    key = f"{CAPTCHA_PREFIX}{captcha_id}"
    stored = cache.get(key)
    if not stored:
        return False
    ok = stored == str(captcha_code).strip().lower()
    if ok and consume:
        cache.delete(key)
    return ok


def create_sms_code(phone):
    code = f"{random.randint(0, 999999):06d}"
    cache.set(f"{SMS_PREFIX}{phone}", code, SMS_TTL)
    cache.set(f"{SMS_COOLDOWN_PREFIX}{phone}", 1, 60)
    return code


def sms_in_cooldown(phone):
    return bool(cache.get(f"{SMS_COOLDOWN_PREFIX}{phone}"))


def clear_sms_send(phone):
    cache.delete(f"{SMS_PREFIX}{phone}")
    cache.delete(f"{SMS_COOLDOWN_PREFIX}{phone}")


def verify_sms_code(phone, code, *, consume=True):
    if not phone or not code:
        return False
    key = f"{SMS_PREFIX}{phone}"
    stored = cache.get(key)
    if not stored:
        return False
    ok = stored == str(code).strip()
    if ok and consume:
        cache.delete(key)
    return ok
