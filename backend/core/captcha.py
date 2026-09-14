import base64
import io
import random
import string
import uuid
from pathlib import Path
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


def _captcha_font(size=40):
    candidates = [
        Path(__file__).resolve().parent.parent / "assets" / "DejaVuSans-Bold.ttf",
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        "arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate) if not isinstance(candidate, Path) else candidate
        try:
            if path.is_file() or candidate == "arial.ttf":
                return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _draw_captcha(text):
    width, height = 220, 72
    image = Image.new("RGB", (width, height), (245, 248, 252))
    draw = ImageDraw.Draw(image)
    font = _captcha_font(40)

    for _ in range(4):
        draw.line(
            (
                random.randint(0, width),
                random.randint(0, height),
                random.randint(0, width),
                random.randint(0, height),
            ),
            fill=(
                random.randint(180, 220),
                random.randint(190, 225),
                random.randint(210, 235),
            ),
            width=1,
        )

    step = width // (len(text) + 1)
    for i, ch in enumerate(text):
        color = (
            random.randint(20, 70),
            random.randint(40, 90),
            random.randint(120, 190),
        )
        x = step * (i + 1) - 12
        y = random.randint(10, 18)
        draw.text((x, y), ch, font=font, fill=color)

    for _ in range(18):
        draw.point(
            (random.randint(0, width - 1), random.randint(0, height - 1)),
            fill=(random.randint(120, 170), random.randint(120, 170), random.randint(140, 190)),
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
