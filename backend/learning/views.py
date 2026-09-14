import json
from urllib.parse import quote
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.mixins import DestroyModelMixin
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from .models import ResearchNote, ResearchReport, LessonPlan, LessonReview, AssistantChat, AssistantMessage
from .serializers import (
    ResearchNoteSerializer,
    ResearchReportSerializer,
    ResearchReportListSerializer,
    LessonPlanSerializer,
    LessonPlanListSerializer,
    LessonReviewSerializer,
    LessonReviewListSerializer,
    AssistantChatSerializer,
    AssistantChatListSerializer,
)
from services.ai import AIServiceError, generate_text, generate_text_stream
from services.asr import AsrError, transcribe_upload
from services.docx_export import markdown_to_docx
from services.file_text import extract_upload_excerpt
from services.notices import push_notice
from services.text_clean import strip_required_marks


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_response(iterator):
    response = StreamingHttpResponse(iterator, content_type="text/event-stream; charset=utf-8")
    response["Cache-Control"] = "no-cache, no-store"
    response["X-Accel-Buffering"] = "no"
    return response


def _docx_response(markdown: str, title: str) -> HttpResponse:
    buffer = markdown_to_docx(markdown, title)
    safe = "".join("_" if ch in '\\/:*?"<>|' else ch for ch in (title or "导出文档"))[:60].strip() or "export"
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    encoded = quote(f"{safe}.docx")
    response["Content-Disposition"] = f"attachment; filename=\"export.docx\"; filename*=UTF-8''{encoded}"
    return response

class OwnerQuerysetMixin:
    def get_queryset(self):
        return self.queryset.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class ResearchNoteViewSet(OwnerQuerysetMixin, viewsets.ModelViewSet):
    queryset = ResearchNote.objects.all()
    serializer_class = ResearchNoteSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        note = serializer.save(author=self.request.user)
        self._merge_file_text(note)
        self._merge_audio_text(note)

    def perform_update(self, serializer):
        note = serializer.save()
        if self.request.FILES.get("source_file"):
            self._merge_file_text(note)
        if self.request.FILES.get("audio_file"):
            self._merge_audio_text(note)

    def _merge_audio_text(self, note):
        if not note.audio_file or (note.content or "").strip():
            return
        try:
            text = transcribe_upload(note.audio_file)
        except AsrError:
            return
        if text:
            note.content = text
            note.save(update_fields=["content"])

    def _merge_file_text(self, note):
        uploaded = note.source_file
        if not uploaded:
            return
        try:
            filename, excerpt = extract_upload_excerpt(uploaded)
        except ValueError:
            return
        if not excerpt:
            return
        note.raw_text = excerpt
        content = (note.content or "").strip()
        if not content:
            note.content = excerpt
        elif excerpt not in content:
            note.content = f"{content}\n\n【来自文件：{filename}】\n{excerpt}"
        note.save(update_fields=["raw_text", "content"])

    @action(detail=False, methods=["post"], url_path="extract")
    def extract(self, request):
        uploaded = request.FILES.get("file") or request.FILES.get("source_file")
        if not uploaded:
            return Response({"detail": "请选择文件"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            filename, excerpt = extract_upload_excerpt(uploaded)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"filename": filename, "excerpt": excerpt})

class ResearchReportViewSet(OwnerQuerysetMixin, DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ResearchReport.objects.prefetch_related("source_notes")
    serializer_class = ResearchReportSerializer
    pagination_class = None

    def get_serializer_class(self):
        if self.action == "list":
            return ResearchReportListSerializer
        return ResearchReportSerializer

    @action(detail=False, methods=["post"])
    def generate(self, request):
        note_ids = request.data.get("note_ids") or []
        report_type = request.data.get("report_type", "weekly")
        notes = ResearchNote.objects.filter(author=request.user, id__in=note_ids)
        if not notes.exists():
            return Response({"detail": "请至少选择一篇笔记"}, status=status.HTTP_400_BAD_REQUEST)
        title = request.data.get("title") or "跟岗研修总结报告"
        user = request.user
        profile = getattr(user, "teacher_profile", None)
        try:
            content = generate_text("note_report", {
                "report_title": title,
                "report_type": report_type,
                "teacher_name": request.data.get("teacher_name") or user.first_name or "",
                "school_name": request.data.get("school_name") or getattr(profile, "school_name", "") or "吴忠市吴忠中学",
                "subject": request.data.get("subject") or getattr(profile, "subject", ""),
                "grade": request.data.get("grade") or getattr(profile, "grade", ""),
                "training_period": request.data.get("training_period", ""),
                "training_base": request.data.get("training_base") or "福建省泉州第一中学",
                "advisor": request.data.get("advisor", ""),
                "report_date": request.data.get("report_date", ""),
                "titles": list(notes.values_list("title", flat=True)),
                "notes": list(notes.values("title", "content", "tags", "subject", "grade")),
            })
        except AIServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        report = ResearchReport.objects.create(author=request.user, title=title, report_type=report_type, content=content)
        report.source_notes.set(notes)
        push_notice(request.user, "report", "研修总结已生成", report.title, f"/reports/{report.id}")
        return Response(self.get_serializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="generate-stream")
    def generate_stream(self, request):
        note_ids = request.data.get("note_ids") or []
        report_type = request.data.get("report_type", "weekly")
        notes = ResearchNote.objects.filter(author=request.user, id__in=note_ids)
        if not notes.exists():
            return Response({"detail": "请至少选择一篇笔记"}, status=status.HTTP_400_BAD_REQUEST)
        title = request.data.get("title") or "跟岗研修总结报告"
        user = request.user
        profile = getattr(user, "teacher_profile", None)
        payload = {
            "report_title": title,
            "report_type": report_type,
            "teacher_name": request.data.get("teacher_name") or user.first_name or "",
            "school_name": request.data.get("school_name") or getattr(profile, "school_name", "") or "吴忠市吴忠中学",
            "subject": request.data.get("subject") or getattr(profile, "subject", ""),
            "grade": request.data.get("grade") or getattr(profile, "grade", ""),
            "training_period": request.data.get("training_period", ""),
            "training_base": request.data.get("training_base") or "福建省泉州第一中学",
            "advisor": request.data.get("advisor", ""),
            "report_date": request.data.get("report_date", ""),
            "titles": list(notes.values_list("title", flat=True)),
            "notes": list(notes.values("title", "content", "tags", "subject", "grade")),
        }
        note_id_list = list(notes.values_list("id", flat=True))

        def events():
            yield ": connected\n\n"
            chunks = []
            try:
                for delta in generate_text_stream("note_report", payload):
                    chunks.append(delta)
                    yield _sse({"delta": delta})
                content = strip_required_marks("".join(chunks))
                report = ResearchReport.objects.create(
                    author=user, title=title, report_type=report_type, content=content,
                )
                report.source_notes.set(note_id_list)
                push_notice(user, "report", "研修总结已生成", report.title, f"/reports/{report.id}")
                yield _sse({"done": True, "id": report.id, "title": report.title})
            except AIServiceError as exc:
                yield _sse({"error": str(exc)})
            except Exception as exc:
                yield _sse({"error": str(exc)})

        return _stream_response(events())

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        report = self.get_object()
        return _docx_response(report.content, report.title)

    @action(detail=True, methods=["patch"], url_path="save")
    def save_content(self, request, pk=None):
        report = self.get_object()
        if "content" in request.data:
            report.content = str(request.data.get("content") or "")
        if request.data.get("title"):
            report.title = str(request.data.get("title"))[:200]
        report.save()
        return Response(self.get_serializer(report).data)

class LessonPlanViewSet(OwnerQuerysetMixin, DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = LessonPlan.objects.all()
    serializer_class = LessonPlanSerializer
    pagination_class = None

    def get_serializer_class(self):
        if self.action == "list":
            return LessonPlanListSerializer
        return LessonPlanSerializer

    @action(detail=False, methods=["post"])
    def generate(self, request):
        required = ["subject", "grade", "topic"]
        missing = [field for field in required if not request.data.get(field)]
        if missing:
            return Response({"detail": f"缺少字段：{', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        profile = getattr(user, "teacher_profile", None)
        payload = {
            "teacher_name": request.data.get("teacher_name") or user.first_name or "",
            "school_name": request.data.get("school_name") or getattr(profile, "school_name", "") or "吴忠市吴忠中学",
            "subject": request.data.get("subject"),
            "grade": request.data.get("grade"),
            "textbook": request.data.get("textbook", ""),
            "class_hours": int(request.data.get("class_hours") or 1),
            "topic": request.data.get("topic"),
            "advisor": request.data.get("advisor", ""),
            "complete_date": request.data.get("complete_date", ""),
            "student_context": request.data.get("student_context", ""),
            "requirements": request.data.get("requirements", ""),
            "program_name": "吴忠中学“组团帮扶”教师跟岗研修项目 · 泉州一中跟岗基地",
        }
        try:
            content = generate_text("lesson_plan", payload)
        except AIServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        plan = LessonPlan.objects.create(
            author=request.user,
            title=request.data.get("title") or f"跟岗研修个人教学设计 · {request.data['topic']}",
            subject=request.data["subject"],
            grade=request.data["grade"],
            topic=request.data["topic"],
            class_hours=int(request.data.get("class_hours") or 1),
            student_context=request.data.get("student_context", ""),
            requirements=request.data.get("requirements", ""),
            generated_content=content,
        )
        push_notice(request.user, "lesson", "教学设计已生成", plan.title, f"/lesson-plans/{plan.id}")
        return Response(self.get_serializer(plan).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="generate-stream")
    def generate_stream(self, request):
        required = ["subject", "grade", "topic"]
        missing = [field for field in required if not request.data.get(field)]
        if missing:
            return Response({"detail": f"缺少字段：{', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        profile = getattr(user, "teacher_profile", None)
        payload = {
            "teacher_name": request.data.get("teacher_name") or user.first_name or "",
            "school_name": request.data.get("school_name") or getattr(profile, "school_name", "") or "吴忠市吴忠中学",
            "subject": request.data.get("subject"),
            "grade": request.data.get("grade"),
            "textbook": request.data.get("textbook", ""),
            "class_hours": int(request.data.get("class_hours") or 1),
            "topic": request.data.get("topic"),
            "advisor": request.data.get("advisor", ""),
            "complete_date": request.data.get("complete_date", ""),
            "student_context": request.data.get("student_context", ""),
            "requirements": request.data.get("requirements", ""),
            "program_name": "吴忠中学“组团帮扶”教师跟岗研修项目 · 泉州一中跟岗基地",
        }
        title = request.data.get("title") or f"跟岗研修个人教学设计 · {request.data['topic']}"

        def events():
            yield ": connected\n\n"
            chunks = []
            try:
                for delta in generate_text_stream("lesson_plan", payload):
                    chunks.append(delta)
                    yield _sse({"delta": delta})
                content = strip_required_marks("".join(chunks))
                plan = LessonPlan.objects.create(
                    author=user,
                    title=title,
                    subject=request.data["subject"],
                    grade=request.data["grade"],
                    topic=request.data["topic"],
                    class_hours=int(request.data.get("class_hours") or 1),
                    student_context=request.data.get("student_context", ""),
                    requirements=request.data.get("requirements", ""),
                    generated_content=content,
                )
                push_notice(user, "lesson", "教学设计已生成", plan.title, f"/lesson-plans/{plan.id}")
                yield _sse({"done": True, "id": plan.id, "title": plan.title})
            except AIServiceError as exc:
                yield _sse({"error": str(exc)})
            except Exception as exc:
                yield _sse({"error": str(exc)})

        return _stream_response(events())

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        plan = self.get_object()
        return _docx_response(plan.generated_content, plan.title)

    @action(detail=True, methods=["patch"], url_path="save")
    def save_content(self, request, pk=None):
        plan = self.get_object()
        if "generated_content" in request.data:
            plan.generated_content = str(request.data.get("generated_content") or "")
        if request.data.get("title"):
            plan.title = str(request.data.get("title"))[:200]
        plan.save()
        return Response(self.get_serializer(plan).data)

class LessonReviewViewSet(OwnerQuerysetMixin, DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = LessonReview.objects.all()
    serializer_class = LessonReviewSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = None

    def get_serializer_class(self):
        if self.action == "list":
            return LessonReviewListSerializer
        return LessonReviewSerializer

    @action(detail=False, methods=["post"])
    def generate(self, request):
        transcript = str(request.data.get("transcript") or "").strip()
        media = request.FILES.get("media_file")
        if not transcript and media:
            try:
                transcript = transcribe_upload(media)
            except AsrError as exc:
                return Response({"detail": f"语音转写失败：{exc}"}, status=status.HTTP_502_BAD_GATEWAY)
        if not transcript:
            return Response({"detail": "请粘贴转写，或上传课堂录音/视频由系统转写"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            content = generate_text("lesson_review", {
                "title": request.data.get("title", "听评课分析"),
                "subject": request.data.get("subject", ""),
                "grade": request.data.get("grade", ""),
                "course_teacher": request.data.get("course_teacher", ""),
                "transcript": transcript,
            })
        except AIServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        item = LessonReview.objects.create(
            author=request.user,
            title=request.data.get("title") or "听评课分析",
            subject=request.data.get("subject", ""),
            grade=request.data.get("grade", ""),
            course_teacher=request.data.get("course_teacher", ""),
            transcript=transcript,
            media_file=request.FILES.get("media_file"),
            report_content=content,
        )
        push_notice(request.user, "review", "听评课报告已生成", item.title, f"/lesson-reviews/{item.id}")
        return Response(self.get_serializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        item = self.get_object()
        return _docx_response(item.report_content, item.title)

    @action(detail=True, methods=["patch"], url_path="save")
    def save_content(self, request, pk=None):
        item = self.get_object()
        if "report_content" in request.data:
            item.report_content = str(request.data.get("report_content") or "")
        if request.data.get("title"):
            item.title = str(request.data.get("title"))[:200]
        item.save()
        return Response(self.get_serializer(item).data)


class AssistantChatViewSet(OwnerQuerysetMixin, viewsets.ModelViewSet):
    queryset = AssistantChat.objects.prefetch_related("messages")
    serializer_class = AssistantChatSerializer
    pagination_class = None

    def get_serializer_class(self):
        if self.action == "list":
            return AssistantChatListSerializer
        return AssistantChatSerializer

    @action(
        detail=False,
        methods=["post"],
        url_path="send-stream",
        parser_classes=[JSONParser, FormParser, MultiPartParser],
    )
    def send_stream(self, request):
        content = str(request.data.get("content") or "").strip()
        uploaded = request.FILES.get("file")
        filename = ""
        file_excerpt = ""
        if uploaded:
            try:
                filename, file_excerpt = extract_upload_excerpt(uploaded)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            uploaded.seek(0)
        if not content and not uploaded:
            return Response({"detail": "请输入问题，或上传要分析的文件"}, status=status.HTTP_400_BAD_REQUEST)
        if not content:
            content = f"请分析我上传的文件「{filename}」。"
        stored = content
        if filename:
            stored = f"{content}\n\n【上传文件：{filename}】\n{file_excerpt}"
        chat_id = request.data.get("chat_id")
        chat = None
        if chat_id:
            chat = AssistantChat.objects.filter(author=request.user, id=chat_id).first()
            if not chat:
                return Response({"detail": "对话不存在"}, status=status.HTTP_404_NOT_FOUND)
        if not chat:
            title_source = content if request.data.get("content") else filename
            chat = AssistantChat.objects.create(author=request.user, title=(title_source or "新对话")[:24])
        AssistantMessage.objects.create(
            chat=chat,
            role="user",
            content=stored,
            attachment=uploaded if uploaded else None,
            attachment_name=filename,
        )
        history = list(chat.messages.values("role", "content"))
        profile = getattr(request.user, "teacher_profile", None)
        payload = {
            "message": content,
            "file_name": filename,
            "file_excerpt": file_excerpt,
            "history": history[:-1],
            "subject": getattr(profile, "subject", "") or "",
            "grade": getattr(profile, "grade", "") or "",
            "school_name": getattr(profile, "school_name", "") or "",
        }

        def events():
            chunks = []
            try:
                yield _sse({"chat_id": chat.id, "title": chat.title})
                for delta in generate_text_stream("assistant_chat", payload):
                    chunks.append(delta)
                    yield _sse({"delta": delta})
                reply = "".join(chunks).strip() or "暂时没有生成回答，请再试一次。"
                AssistantMessage.objects.create(chat=chat, role="assistant", content=reply)
                chat.save(update_fields=["updated_at"])
                yield _sse({"done": True, "chat_id": chat.id, "title": chat.title})
            except AIServiceError as exc:
                yield _sse({"error": str(exc)})
            except Exception as exc:
                yield _sse({"error": str(exc)})

        return _stream_response(events())
