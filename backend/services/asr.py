import json
import os
import tempfile
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

ASR_MAX_BYTES = 80 * 1024 * 1024
AUDIO_EXT = {
    ".mp3", ".wav", ".m4a", ".aac", ".amr", ".flac", ".ogg", ".wma",
    ".mp4", ".mov", ".webm", ".avi", ".mkv", ".mpeg", ".mpg",
}


class AsrError(RuntimeError):
    pass


def _api_key() -> str:
    return os.getenv("AI_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")


def _model() -> str:
    return os.getenv("ASR_MODEL", "paraformer-v2")


def _base_url() -> str:
    return os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/api/v1").rstrip("/")


def _json_request(url, *, method="GET", headers=None, payload=None, timeout=60):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="ignore")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            err = json.loads(body)
            message = err.get("message") or err.get("Message") or body
        except Exception:
            message = body or str(exc)
        raise AsrError(f"语音识别接口失败：{message}") from exc
    except AsrError:
        raise
    except Exception as exc:
        raise AsrError(f"语音识别接口失败：{exc}") from exc


def _multipart_post(url, fields: dict, filename: str, file_bytes: bytes, content_type: str):
    boundary = f"----DashScope{uuid.uuid4().hex}"
    body = BytesIO()
    for name, value in fields.items():
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.write(str(value).encode("utf-8"))
        body.write(b"\r\n")
    body.write(f"--{boundary}\r\n".encode())
    safe_name = filename.replace('"', "")
    body.write(
        f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'.encode("utf-8")
    )
    body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.write(file_bytes)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    request = urllib.request.Request(url, data=body.getvalue(), method="POST")
    request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise AsrError(f"音频上传失败：{body or exc}") from exc


def _upload_temp_oss(api_key: str, model: str, file_path: str, filename: str) -> str:
    policy = _json_request(
        f"{_base_url()}/uploads?{urllib.parse.urlencode({'action': 'getPolicy', 'model': model})}",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    data = policy.get("data") or policy
    upload_host = data.get("upload_host")
    upload_dir = data.get("upload_dir")
    if not upload_host or not upload_dir:
        raise AsrError("无法获取语音识别上传凭证，请确认百炼 API Key 已开通语音识别")
    key = f"{upload_dir}/{filename}"
    file_bytes = Path(file_path).read_bytes()
    ctype = "application/octet-stream"
    fields = {
        "OSSAccessKeyId": data.get("oss_access_key_id") or "",
        "Signature": data.get("signature") or "",
        "policy": data.get("policy") or "",
        "x-oss-object-acl": data.get("x_oss_object_acl") or "private",
        "x-oss-forbid-overwrite": data.get("x_oss_forbid_overwrite") or "true",
        "key": key,
        "success_action_status": "200",
    }
    status = _multipart_post(upload_host, fields, filename, file_bytes, ctype)
    if status not in (200, 204):
        raise AsrError("音频上传失败")
    return f"oss://{key}"


def _submit_task(api_key: str, model: str, file_url: str) -> str:
    payload = {
        "model": model,
        "input": {"file_urls": [file_url]},
        "parameters": {"language_hints": ["zh", "en"]},
    }
    data = _json_request(
        f"{_base_url()}/services/audio/asr/transcription",
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
            "X-DashScope-OssResourceResolve": "enable",
        },
        payload=payload,
        timeout=60,
    )
    task_id = (data.get("output") or {}).get("task_id")
    if not task_id:
        raise AsrError(data.get("message") or "语音识别任务提交失败")
    return task_id


def _poll_task(api_key: str, task_id: str) -> dict:
    url = f"{_base_url()}/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            data = _json_request(url, method="GET", headers=headers, timeout=30)
        except AsrError:
            data = _json_request(url, method="POST", headers=headers, timeout=30)
        output = data.get("output") or data
        status = str(output.get("task_status") or "").upper()
        if status == "SUCCEEDED":
            return output
        if status in {"FAILED", "UNKNOWN"}:
            results = output.get("results") or []
            message = ""
            if results:
                message = results[0].get("message") or results[0].get("code") or ""
            raise AsrError(message or "语音识别失败")
        time.sleep(2)
    raise AsrError("语音识别超时，请改用更短的录音后重试")


def _extract_text(output: dict) -> str:
    results = output.get("results") or []
    texts = []
    for item in results:
        if str(item.get("subtask_status") or "").upper() == "FAILED":
            raise AsrError(item.get("message") or "语音识别失败")
        url = item.get("transcription_url")
        if not url:
            continue
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        except Exception as exc:
            raise AsrError(f"读取转写结果失败：{exc}") from exc
        for transcript in payload.get("transcripts") or []:
            text = (transcript.get("text") or "").strip()
            if text:
                texts.append(text)
    return "\n".join(texts).strip()


def transcribe_file(file_path: str, filename: str = "") -> str:
    api_key = _api_key()
    if not api_key:
        raise AsrError("未配置百炼 API Key，无法转写音频")
    path = Path(file_path)
    if not path.exists():
        raise AsrError("音频文件不存在")
    size = path.stat().st_size
    if size > ASR_MAX_BYTES:
        raise AsrError("音视频不能超过 80MB")
    if size < 200:
        raise AsrError("音频文件过短，请重新录制或上传")
    name = filename or path.name
    ext = Path(name).suffix.lower()
    if ext and ext not in AUDIO_EXT:
        raise AsrError("请上传 mp3 / wav / m4a / mp4 等常见音视频")
    model = _model()
    oss_url = _upload_temp_oss(api_key, model, str(path), name)
    task_id = _submit_task(api_key, model, oss_url)
    output = _poll_task(api_key, task_id)
    text = _extract_text(output)
    if not text:
        raise AsrError("没有识别到有效语音，请确认录音清晰后重试")
    return text


def transcribe_upload(uploaded) -> str:
    name = Path(getattr(uploaded, "name", "") or "audio.mp3").name
    ext = Path(name).suffix.lower() or ".mp3"
    size = int(getattr(uploaded, "size", 0) or 0)
    if size > ASR_MAX_BYTES:
        raise AsrError("音视频不能超过 80MB")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        uploaded.seek(0)
        for chunk in uploaded.chunks():
            tmp.write(chunk)
        tmp.close()
        return transcribe_file(tmp.name, filename=name)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        try:
            uploaded.seek(0)
        except Exception:
            pass
