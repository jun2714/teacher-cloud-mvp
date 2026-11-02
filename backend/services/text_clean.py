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


# 程序内部字段名，不应出现在给老师看的正文里。
# 只收录不会在正常教学内容中出现的标识符；subject、grade、title 等普通英文词不在此列，
# 以免误改英语课材料。
INTERNAL_FIELD_LABELS = {
    "transcript": "材料正文",
    "material_kind": "材料类型",
    "material_sources": "材料来源",
    "course_teacher": "授课教师",
    "student_context": "学情说明",
    "teacher_name": "教师姓名",
    "school_name": "所在单位",
    "class_hours": "课时安排",
    "complete_date": "完成日期",
    "training_period": "跟岗时间",
    "training_base": "跟岗基地",
    "report_date": "报告日期",
    "report_type": "报告类型",
    "report_title": "报告标题",
    "file_excerpt": "文件内容",
    "file_name": "文件名",
    "program_name": "项目名称",
    "payload": "所提供材料",
}
_FIELD_KEYS = "|".join(sorted(INTERNAL_FIELD_LABELS, key=len, reverse=True))
# “仅基于提供的 JSON `transcript` 字段内容” → “仅基于所提供材料”
_JSON_FIELD_PHRASE = re.compile(
    r"(?:所?提供的|输入的?|原始的?)?\s*JSON\s*(?:数据|资料|格式|对象|文件)?\s*(?:中的?|里的?|的)?\s*"
    r"`?(?:" + _FIELD_KEYS + r")`?\s*字段(?:的)?(?:内容|文本|数据)?(?:中|里)?"
)
_JSON_ONLY_PHRASE = re.compile(
    r"(?:所?提供的|输入的?|原始的?|以下|上述)\s*JSON\s*(?:数据|资料|格式|对象|内容)?(?:中|里)?"
)
_BACKTICK_FIELD = re.compile(r"`(" + _FIELD_KEYS + r")`\s*(?:字段)?")
_BARE_FIELD = re.compile(r"(?<![A-Za-z_])(" + _FIELD_KEYS + r")(?![A-Za-z_])\s*字段")


def strip_internal_terms(text: str) -> str:
    """把 AI 误写进正文的 JSON、英文字段名换成中文说法。"""
    if not text:
        return text
    text = _JSON_FIELD_PHRASE.sub("所提供材料", text)
    text = _JSON_ONLY_PHRASE.sub("所提供材料", text)
    text = _BACKTICK_FIELD.sub(lambda m: INTERNAL_FIELD_LABELS[m.group(1)], text)
    text = _BARE_FIELD.sub(lambda m: INTERNAL_FIELD_LABELS[m.group(1)], text)
    text = text.replace("提供的所提供材料", "所提供材料").replace("所提供的所提供材料", "所提供材料")
    return text


_TRANSCRIPT_NOUN = re.compile(r"(?:课堂)?(?:录音|语音|音频|音视频)?转写(?:后的)?(?:文本|内容|文字|记录|稿)")


def replace_transcript_wording(text: str, source_phrase: str) -> str:
    """材料不是录音时，把“转写文本”之类的说法改成真实来源。"""
    if not text:
        return text
    return _TRANSCRIPT_NOUN.sub(source_phrase, text)


def clean_generated_text(text: str) -> str:
    return strip_internal_terms(strip_required_marks(text))
