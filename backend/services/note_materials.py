"""Note imports: strict document/vision extraction plus plain text formats."""
from pathlib import Path

from services.file_text import TEXT_EXT, _decode_bytes
from services.review_materials import (
    ALLOWED_EXT, MAX_BYTES, MAX_CHARS, MaterialError, extract_review_material,
)

NOTE_EXT = ALLOWED_EXT | TEXT_EXT


def extract_note_material(uploaded):
    ext = Path(uploaded.name).suffix.lower()
    if ext not in TEXT_EXT:
        result = extract_review_material(uploaded)
        return {"filename": result["filename"], "excerpt": result["text"], "warnings": result["warnings"]}
    if uploaded.size > MAX_BYTES:
        raise MaterialError("文件不能超过 8MB")
    try:
        uploaded.seek(0)
        data = uploaded.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise MaterialError("文件不能超过 8MB")
        text = _decode_bytes(data).strip()
        if not text:
            raise MaterialError("文件没有可用正文，请重新选择或手动输入")
        if len(text) > MAX_CHARS:
            raise MaterialError("文件正文超过 60000 字，请拆分后导入")
        return {"filename": Path(uploaded.name).name, "excerpt": text, "warnings": []}
    finally:
        uploaded.seek(0)
