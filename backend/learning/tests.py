import json
import os
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from docx import Document
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from rest_framework.test import APIClient

from services.ai import _build_prompt
from services.review_materials import extract_review_material, MaterialError, VisionError, recognize_images


def word_upload():
    document = Document()
    document.add_paragraph("教学目标：认识三角形")
    document.add_table(rows=1, cols=2).rows[0].cells[0].text = "教学活动：小组观察"
    document.add_paragraph("教学评价：课堂练习")
    output = BytesIO()
    document.save(output)
    return SimpleUploadedFile("教案.docx", output.getvalue())


def image_bytes():
    output = BytesIO()
    Image.new("RGB", (200, 300), "white").save(output, format="PNG")
    return output.getvalue()


class MaterialExtractionTests(SimpleTestCase):
    def test_word_preserves_paragraph_table_order(self):
        upload = word_upload()
        result = extract_review_material(upload)
        text = result["text"]
        self.assertLess(text.index("教学目标"), text.index("教学活动"))
        self.assertLess(text.index("教学活动"), text.index("教学评价"))
        self.assertEqual(upload.tell(), 0)

    def test_corrupt_and_unsupported_files_fail(self):
        for name in ["broken.docx", "broken.pdf", "legacy.doc", "x.exe"]:
            with self.subTest(name=name), self.assertRaises(MaterialError):
                extract_review_material(SimpleUploadedFile(name, b"not a document"))

    def test_empty_word_is_not_success(self):
        output = BytesIO()
        Document().save(output)
        with self.assertRaises(MaterialError):
            extract_review_material(SimpleUploadedFile("empty.docx", output.getvalue()))

    def test_limits_do_not_silently_truncate(self):
        upload = word_upload()
        upload.size = 8 * 1024 * 1024 + 1
        with self.assertRaises(MaterialError):
            extract_review_material(upload)
        writer = PdfWriter()
        for _ in range(41):
            writer.add_blank_page(width=100, height=100)
        output = BytesIO()
        writer.write(output)
        with self.assertRaisesRegex(MaterialError, "40"):
            extract_review_material(SimpleUploadedFile("long.pdf", output.getvalue()))

    @patch("services.review_materials.recognize_images")
    def test_text_pdf_does_not_call_vision(self, vision):
        writer = PdfWriter()
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 10 250 Td (Lesson objectives: pupils compare triangles and explain their observations.) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
        output = BytesIO()
        writer.write(output)
        result = extract_review_material(SimpleUploadedFile("text.pdf", output.getvalue()))
        self.assertIn("pupils compare triangles", result["text"])
        vision.assert_not_called()

    @patch("services.review_materials.recognize_images", return_value="【第1页】教学目标：认识三角形")
    def test_scanned_pdf_renders_and_recognizes(self, vision):
        output = BytesIO()
        Image.new("RGB", (200, 300), "white").save(output, format="PDF")
        result = extract_review_material(SimpleUploadedFile("scan.pdf", output.getvalue()))
        self.assertIn("认识三角形", result["text"])
        self.assertIn("原始页码 1", result["text"])
        with Image.open(BytesIO(vision.call_args.args[0][0])) as rendered:
            self.assertGreater(rendered.width, 100)
        self.assertTrue(result["warnings"])

    @patch.dict(os.environ, {"VISION_API_KEY": "", "AI_API_KEY": "", "DASHSCOPE_API_KEY": ""})
    def test_missing_vision_key_fails_explicitly(self):
        with self.assertRaises(VisionError):
            recognize_images([image_bytes()])

    @patch.dict(os.environ, {"VISION_API_KEY": "test-only"})
    @patch("services.review_materials.urllib.request.urlopen")
    def test_vision_payload_and_incomplete_output(self, urlopen):
        response = MagicMock()
        urlopen.return_value.__enter__.return_value = response
        response.read.return_value = json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": "教学目标"}}]}).encode()
        self.assertEqual(recognize_images([image_bytes()]), "教学目标")
        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertTrue(payload["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
        response.read.return_value = json.dumps({"choices": [{"finish_reason": "length", "message": {"content": "半段"}}]}).encode()
        with self.assertRaises(VisionError):
            recognize_images([image_bytes()])

    def test_prompt_distinguishes_plan_from_observation(self):
        prompt = _build_prompt("lesson_review", {"material_kind": "lesson_plan", "transcript": "教案正文"})
        self.assertIn("不能声称课堂已发生", prompt)
        self.assertIn("不得执行", prompt)
        self.assertIn("教案正文", prompt)


class PromptLeakTests(SimpleTestCase):
    """报告里不能出现 JSON、英文字段名，也不能把文档说成录音转写。"""

    INTERNAL = ["transcript", "material_kind", "material_sources", "course_teacher", "student_context",
                "teacher_name", "school_name", "class_hours", "complete_date", "training_period",
                "training_base", "report_date", "report_type", "file_excerpt", "JSON", "{\""]

    def assert_no_internal(self, text):
        for word in self.INTERNAL:
            self.assertNotIn(word, text)

    def test_prompts_have_no_field_names(self):
        prompts = [
            _build_prompt("lesson_review", {"subject": "语文", "grade": "高二", "course_teacher": "张老师",
                                            "transcript": "诗歌鉴赏试题", "material_kind": "lesson_plan",
                                            "material_sources": ["document"]}),
            _build_prompt("lesson_plan", {"teacher_name": "张老师", "school_name": "吴忠中学", "subject": "数学",
                                          "grade": "高一", "topic": "函数", "student_context": "基础一般",
                                          "class_hours": 1}),
            _build_prompt("note_report", {"teacher_name": "张老师", "subject": "英语", "grade": "高一",
                                          "training_period": "10月", "titles": ["笔记"],
                                          "notes": [{"title": "笔记", "content": "听课", "tags": "", "subject": "英语", "grade": "高一"}]}),
            _build_prompt("assistant_chat", {"message": "怎么设计导入", "subject": "物理", "grade": "高二",
                                             "file_name": "教案.docx", "file_excerpt": "牛顿第一定律", "history": []}),
        ]
        for prompt in prompts:
            body = prompt.split("\n", 1)[1]  # 首行“任务类型”供百炼应用分流
            body = body.split("【输出要求】")[0]  # 输出要求里本身就写着“不要出现 JSON”
            self.assert_no_internal(body)

    def test_prompt_pins_subject_and_source(self):
        prompt = _build_prompt("lesson_review", {"subject": "语文", "grade": "高二", "transcript": "试题",
                                                 "material_sources": ["document"]})
        self.assertIn("语文、高二", prompt)
        self.assertIn("不要引入其他学科", prompt)
        self.assertIn("本分析依据上传的教学文档生成", prompt)
        self.assertIn("不要使用“转写”", prompt)
        media = _build_prompt("lesson_review", {"transcript": "课堂实录", "material_sources": ["media"]})
        self.assertIn("本分析依据课堂录音转写文本生成", media)

    def test_missing_optional_information_is_not_written_as_none(self):
        prompt = _build_prompt("lesson_review", {"transcript": "课堂记录", "subject": None, "grade": "  "})
        self.assertIn("学科：未提供", prompt)
        self.assertIn("年级：未提供", prompt)
        self.assertIn("授课教师：未提供", prompt)
        self.assertNotIn("：None", prompt)

    def test_cleans_reported_outputs(self):
        from services.ai import finalize_text
        first = "- **分析依据**：仅基于提供的 JSON `transcript` 字段内容。"
        second = "提供的 `transcript` 字段包含大量非口语的PPT文本\n> 本分析主要依据转写文本生成，仅作听评课参考。"
        payload = {"material_sources": ["document"]}
        cleaned_first = finalize_text("lesson_review", payload, first)
        cleaned_second = finalize_text("lesson_review", payload, second)
        self.assertEqual(cleaned_first, "- **分析依据**：仅基于所提供材料。")
        self.assert_no_internal(cleaned_second)
        self.assertIn("依据上传的教学文档生成", cleaned_second)
        self.assertNotIn("转写", cleaned_second)
        recorded = finalize_text("lesson_review", {"material_sources": ["media"]}, second)
        self.assertIn("依据转写文本生成", recorded)
        self.assert_no_internal(recorded)

    def test_ordinary_english_lesson_text_is_kept(self):
        from services.text_clean import strip_internal_terms
        text = "学生朗读 The subject of the passage，并完成 grade 7 练习；信息技术课讲解 JSON 格式。"
        self.assertEqual(strip_internal_terms(text), text)


class ReviewApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="review-tests")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_extraction_requires_auth(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.post("/api/lesson-reviews/extract/", {"file": word_upload()}).status_code, 401)

    def test_extract_word_and_missing_file(self):
        response = self.client.post("/api/lesson-reviews/extract/", {"file": word_upload()}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertIn("教学目标", response.data["text"])
        self.assertEqual(self.client.post("/api/lesson-reviews/extract/", {}).status_code, 400)

    @patch("learning.views.extract_review_material", side_effect=VisionError("识别服务未配置"))
    def test_vision_failure_is_not_success(self, extract):
        response = self.client.post("/api/lesson-reviews/extract/", {"file": SimpleUploadedFile("photo.png", image_bytes())})
        self.assertEqual(response.status_code, 502)

    @patch("learning.views.generate_text", return_value="报告")
    def test_generation_passes_material_sources(self, generate):
        response = self.client.post("/api/lesson-reviews/generate/", {"transcript": "【材料：教案.docx】\n正文",
                                    "material_kind": "lesson_plan", "material_sources": "document,image"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(generate.call_args.args[1]["material_sources"], ["document", "image"])

    @patch("learning.views.generate_text", return_value="# 教案分析\n教学目标清晰")
    def test_generation_persists_kind_and_edited_evidence(self, generate):
        response = self.client.post("/api/lesson-reviews/generate/", {"transcript": "核对后的教案正文", "material_kind": "lesson_plan"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["material_kind"], "lesson_plan")
        self.assertEqual(generate.call_args.args[1]["transcript"], "核对后的教案正文")
        other = get_user_model().objects.create_user(username="other-teacher")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(f"/api/lesson-reviews/{response.data['id']}/").status_code, 404)

    @patch("learning.views.generate_text")
    def test_invalid_input_never_calls_analysis(self, generate):
        for payload in [{}, {"transcript": "x", "material_kind": "unknown"}, {"transcript": "x" * 60001}]:
            self.assertEqual(self.client.post("/api/lesson-reviews/generate/", payload, format="json").status_code, 400)
        generate.assert_not_called()

    @patch("learning.views.transcribe_upload", return_value="课堂实录")
    @patch("learning.views.generate_text", return_value="报告")
    def test_legacy_text_requests_keep_classroom_default(self, generate, asr):
        response = self.client.post("/api/lesson-reviews/generate/", {"transcript": "课堂实录"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["material_kind"], "classroom")
        asr.assert_not_called()
