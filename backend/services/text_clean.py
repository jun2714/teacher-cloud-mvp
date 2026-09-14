import re

# 表单必填星号：姓名*、**姓名***、1. 个人教学改进*
_BOLD_EXTRA_STAR = re.compile(r"\*\*([^*\n]+?)\*\*\*")
_LABEL_STAR_COLON = re.compile(r"([\u4e00-\u9fff])\*([：:])")
_LABEL_STAR_LINE = re.compile(
    r"^(\s*(?:\d+[\.、]\s*)?[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9/]*)\*\s*$",
    re.M,
)


def strip_required_marks(text: str) -> str:
    if not text:
        return text
    text = _BOLD_EXTRA_STAR.sub(r"**\1**", text)
    text = _LABEL_STAR_COLON.sub(r"\1\2", text)
    text = _LABEL_STAR_LINE.sub(r"\1", text)
    return text
