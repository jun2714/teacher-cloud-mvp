import re

# 表单必填星号：姓名*、**姓名***、1. 个人教学改进*
_STAR_TRANSLATE = str.maketrans({"＊": "*", "∗": "*", "﹡": "*"})
_BOLD_EXTRA_STAR = re.compile(r"\*\*([^*\n]+?)\*\*\s*\*+\s*(?=[：:])")
_ITALIC_LABEL = re.compile(r"(^|[^*\n])\*([^*\n]{1,24})\*(?=\s*[：:])")
_LABEL_STAR_COLON = re.compile(r"([\u4e00-\u9fffA-Za-z0-9])\*(?=[：:])")
_LABEL_STAR_LINE = re.compile(
    r"^(\s*(?:\d+[\.、]\s*)?[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9/（）()]{0,30})\*+\s*$",
    re.M,
)
_BR = re.compile(r"<br\s*/?>", re.I)
_BR_ONLY_LINE = re.compile(r"^[ \t]*(?:\u2028)+[ \t]*$", re.M)
_ELLIPSIS_LINE = re.compile(r"^[ \t]*(?:\.{3,}|…{1,}|·{3,}|。{3,})[ \t]*$", re.M)
_HR_LINE = re.compile(r"^[ \t]*([-*_])\1{2,}[ \t]*$", re.M)


def strip_required_marks(text: str) -> str:
    """去掉导出和展示里不该出现的星号、<br>、单独省略号和分隔线。"""
    if not text:
        return text
    text = text.translate(_STAR_TRANSLATE)
    text = _BOLD_EXTRA_STAR.sub(r"**\1**", text)
    text = _ITALIC_LABEL.sub(r"\1\2", text)
    text = _LABEL_STAR_COLON.sub(r"\1", text)
    text = _LABEL_STAR_LINE.sub(r"\1", text)
    text = _BR.sub("\u2028", text)
    text = _BR_ONLY_LINE.sub("", text)
    text = _ELLIPSIS_LINE.sub("", text)
    text = _HR_LINE.sub("", text)
    return text
