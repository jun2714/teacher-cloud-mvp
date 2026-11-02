import re

from django.db import migrations

from services.text_clean import replace_transcript_wording, strip_internal_terms

SOURCE_PHRASES = {
    "document": "上传的教学文档",
    "image": "教案图片识别文字",
    "text": "教师提供的文字材料",
}
_MATERIAL_NAME = re.compile(r"【材料：[^】]*?\.([A-Za-z0-9]+)】")
_IMAGE_EXT = {"jpg", "jpeg", "png", "webp"}
_MEDIA_EXT = {"mp3", "wav", "m4a", "aac", "amr", "flac", "ogg", "wma", "mp4", "mov", "webm", "avi", "mkv", "mpeg", "mpg"}


def _review_source_phrase(review):
    if review.media_file:
        return None
    exts = {ext.lower() for ext in _MATERIAL_NAME.findall(review.transcript or "")}
    if exts & _MEDIA_EXT:
        return None
    sources = []
    if exts - _IMAGE_EXT:
        sources.append("document")
    if exts & _IMAGE_EXT:
        sources.append("image")
    return "和".join(SOURCE_PHRASES[s] for s in sources or ["text"])


def clean_existing(apps, schema_editor):
    alias = schema_editor.connection.alias
    for model_name, field in [
        ("LessonPlan", "generated_content"),
        ("ResearchReport", "content"),
    ]:
        model = apps.get_model("learning", model_name)
        for obj in model.objects.using(alias).only("id", field):
            old = getattr(obj, field) or ""
            new = strip_internal_terms(old)
            if new != old:
                model.objects.using(alias).filter(pk=obj.pk).update(**{field: new})

    LessonReview = apps.get_model("learning", "LessonReview")
    for review in LessonReview.objects.using(alias).all():
        old = review.report_content or ""
        new = strip_internal_terms(old)
        phrase = _review_source_phrase(review)
        if phrase:
            new = replace_transcript_wording(new, phrase)
        if new != old:
            LessonReview.objects.using(alias).filter(pk=review.pk).update(report_content=new)

    AssistantMessage = apps.get_model("learning", "AssistantMessage")
    for message in AssistantMessage.objects.using(alias).filter(role="assistant").only("id", "content"):
        old = message.content or ""
        new = strip_internal_terms(old)
        if new != old:
            AssistantMessage.objects.using(alias).filter(pk=message.pk).update(content=new)


class Migration(migrations.Migration):
    dependencies = [("learning", "0005_update_program_name")]
    operations = [migrations.RunPython(clean_existing, migrations.RunPython.noop)]
