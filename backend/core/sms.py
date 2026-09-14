import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

from django.conf import settings

logger = logging.getLogger(__name__)


class SmsError(RuntimeError):
    pass


def _friendly_sms_error(ali_code: str, message: str | None = None) -> str:
    code = (ali_code or "").strip()
    mapping = {
        "SignatureDoesNotMatch": "短信签名校验失败，请核对 AccessKey 与短信签名名称是否与控制台一致",
        "InvalidAccessKeyId.NotFound": "短信 AccessKey 无效",
        "Forbidden.RAM": "当前 AccessKey 没有短信发送权限",
        "isv.SMS_SIGNATURE_ILLEGAL": "短信签名未审核通过，或与控制台名称不一致",
        "isv.SMS_TEMPLATE_ILLEGAL": "短信模板未审核通过，或模板 CODE 不正确",
        "isv.BUSINESS_LIMIT_CONTROL": "短信发送过于频繁，请稍后再试",
        "isv.MOBILE_NUMBER_ILLEGAL": "手机号格式不正确",
        "isv.AMOUNT_NOT_ENOUGH": "短信账户余额不足",
    }
    if code in mapping:
        return mapping[code]
    return "短信发送失败，请稍后重试"


def _percent_encode(value: str) -> str:
    # 与 Java URLEncoder + 阿里云 POP 规则一致：- _ . ~ 不编码
    encoded = urllib.parse.quote(str(value), safe="-_.~")
    return encoded.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")


def _sign(params: dict, secret: str, method: str = "POST") -> str:
    canonical = "&".join(
        f"{_percent_encode(k)}={_percent_encode(v)}"
        for k, v in sorted(params.items())
    )
    string_to_sign = f"{method}&%2F&{_percent_encode(canonical)}"
    digest = hmac.new(
        f"{secret}&".encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def send_aliyun_sms(phone: str, code: str) -> None:
    if not settings.SMS_ENABLED:
        raise SmsError("短信服务未开启")

    access_key_id = settings.SMS_ACCESS_KEY_ID
    access_key_secret = settings.SMS_ACCESS_KEY_SECRET
    sign_name = settings.SMS_SIGN_NAME
    template_code = settings.SMS_TEMPLATE_ID
    if not all([access_key_id, access_key_secret, sign_name, template_code]):
        raise SmsError("短信服务配置不完整")

    params = {
        "AccessKeyId": access_key_id,
        "Action": "SendSms",
        "Format": "JSON",
        "PhoneNumbers": phone,
        "RegionId": settings.SMS_REGION_ID or "cn-hangzhou",
        "SignName": sign_name,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": uuid.uuid4().hex,
        "SignatureVersion": "1.0",
        "TemplateCode": template_code,
        "TemplateParam": json.dumps({"code": code}, ensure_ascii=False, separators=(",", ":")),
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }
    params["Signature"] = _sign(params, access_key_secret, "POST")
    body = "&".join(
        f"{_percent_encode(k)}={_percent_encode(v)}"
        for k, v in params.items()
    )
    request = urllib.request.Request(
        f"https://{settings.SMS_ENDPOINT or 'dysmsapi.aliyuncs.com'}/",
        data=body.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        ali_code = ""
        try:
            ali_code = str(json.loads(raw).get("Code") or "")
        except Exception:
            ali_code = ""
        logger.exception("阿里云短信 HTTP 错误: status=%s code=%s", exc.code, ali_code or "unknown")
        raise SmsError(_friendly_sms_error(ali_code)) from exc
    except Exception as exc:
        logger.exception("阿里云短信调用失败")
        raise SmsError("短信发送失败，请稍后重试") from exc

    ali_code = str(payload.get("Code") or "")
    if ali_code != "OK":
        logger.error("阿里云短信业务失败: code=%s message=%s", ali_code, payload.get("Message"))
        raise SmsError(_friendly_sms_error(ali_code, payload.get("Message")))
