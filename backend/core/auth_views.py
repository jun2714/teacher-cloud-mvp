import re
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .captcha import (
    clear_sms_send,
    create_captcha,
    create_sms_code,
    sms_in_cooldown,
    verify_captcha,
    verify_sms_code,
)
from .serializers import UserSerializer
from .sms import SmsError, send_aliyun_sms
from .tokens import blacklist_refresh

PHONE_RE = re.compile(r"^1\d{10}$")
DEFAULT_PASSWORD = "123456"


def build_default_username(phone: str) -> str:
    """默认账号：手机号后四位_用户；冲突时追加区分后缀。"""
    base = f"{phone[-4:]}_用户"
    if not User.objects.filter(username=base).exists():
        return base
    for suffix in range(2, 100):
        candidate = f"{base}{suffix}"
        if not User.objects.filter(username=candidate).exists():
            return candidate
    return f"{phone}_用户"


def find_user_by_account(account: str):
    account = str(account or "").strip()
    if not account:
        return None
    if PHONE_RE.match(account):
        return User.objects.filter(email=account).first()
    return User.objects.filter(username=account).first()


def issue_auth_response(user, detail, *, extra=None, status_code=status.HTTP_200_OK):
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    refresh = RefreshToken.for_user(user)
    payload = {
        "detail": detail,
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }
    if extra:
        payload.update(extra)
    return Response(payload, status=status_code)


class PhoneOrUsernameTokenSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": "手机号或密码错误",
    }

    def validate(self, attrs):
        account = str(attrs.get(self.username_field, "")).strip()
        user = find_user_by_account(account)
        if user:
            attrs[self.username_field] = user.username
        data = super().validate(attrs)
        self.user.last_login = timezone.now()
        self.user.save(update_fields=["last_login"])
        return data


class PhoneOrUsernameTokenView(TokenObtainPairView):
    serializer_class = PhoneOrUsernameTokenSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def captcha(request):
    return Response(create_captcha())


@api_view(["POST"])
@permission_classes([AllowAny])
def send_sms_code(request):
    phone = str(request.data.get("phone", "")).strip()
    captcha_id = request.data.get("captcha_id", "")
    captcha_code = request.data.get("captcha_code", "")

    if not PHONE_RE.match(phone):
        return Response({"detail": "请输入正确的手机号"}, status=status.HTTP_400_BAD_REQUEST)
    if not verify_captcha(captcha_id, captcha_code, consume=True):
        return Response({"detail": "图形验证码错误或已过期"}, status=status.HTTP_400_BAD_REQUEST)
    if sms_in_cooldown(phone):
        return Response({"detail": "验证码发送过于频繁，请稍后再试"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    code = create_sms_code(phone)
    payload = {
        "detail": "验证码已发送",
        "expires_in": 300,
        "cooldown": 60,
    }

    if settings.SMS_ENABLED:
        try:
            send_aliyun_sms(phone, code)
        except SmsError as exc:
            clear_sms_send(phone)
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(payload)

    if settings.DEBUG:
        payload["demo_code"] = code
        payload["detail"] = "短信服务未开启，已返回演示验证码"
    return Response(payload)


def auth_by_sms(phone, sms_code):
    phone = str(phone or "").strip()
    sms_code = str(sms_code or "").strip()
    if not PHONE_RE.match(phone):
        return Response({"detail": "请输入正确的手机号"}, status=status.HTTP_400_BAD_REQUEST)
    if not verify_sms_code(phone, sms_code, consume=True):
        return Response({"detail": "短信验证码错误或已过期"}, status=status.HTTP_400_BAD_REQUEST)

    existing = User.objects.filter(email=phone).first()
    if existing:
        return issue_auth_response(existing, "登录成功", extra={"existing": True})

    username = build_default_username(phone)
    user = User.objects.create_user(
        username=username,
        password=DEFAULT_PASSWORD,
        first_name=username,
        email=phone,
    )
    return issue_auth_response(
        user,
        "注册成功，初始密码为 123456，请到设置中修改",
        extra={"default_username": username, "existing": False},
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def sms_login(request):
    return auth_by_sms(request.data.get("phone"), request.data.get("sms_code"))


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    return auth_by_sms(request.data.get("phone"), request.data.get("sms_code"))


@api_view(["POST"])
@permission_classes([AllowAny])
def logout(request):
    blacklist_refresh(request.data.get("refresh") if hasattr(request, "data") else "")
    return Response({"detail": "已退出"})
