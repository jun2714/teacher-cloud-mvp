import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from learning.models import ResearchNote
from learning.tests import word_upload, image_bytes
from services.review_materials import VisionError


class NoteWorkflowTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        override = override_settings(MEDIA_ROOT=media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.user = get_user_model().objects.create_user(username="note-owner")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_file_save_preserves_corrections_and_reopen_and_delete(self):
        response = self.client.post('/api/notes/', {
            'title': '导入并修订', 'content': '老师修改后的教学目标',
            'raw_text': '识别原文', 'input_method': 'file', 'tags': '["教学设计", "反思"]',
            'source_file': word_upload(),
        }, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['content'], '老师修改后的教学目标')
        self.assertEqual(response.data['raw_text'], '识别原文')
        self.assertEqual(response.data['tags'], ['教学设计', '反思'])
        self.assertTrue(response.data['source_file_url'])
        url = f"/api/notes/{response.data['id']}/"
        self.assertEqual(self.client.get(url).data['content'], '老师修改后的教学目标')
        edited = self.client.patch(url, {
            'content': '再次修改的正文', 'source_file': word_upload(), 'raw_text': '新的识别原文',
        }, format='multipart')
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.data['content'], '再次修改的正文')
        # A later text-only edit preserves existing attachments.
        edited = self.client.patch(url, {'content': '最终正文'}, format='json')
        self.assertEqual(edited.data['content'], '最终正文')
        self.assertTrue(edited.data['source_file_url'])
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_audio_save_keeps_reviewed_transcript(self):
        response = self.client.post('/api/notes/', {
            'title': '听课录音', 'content': '修订后的转写内容', 'input_method': 'voice',
            'audio_file': SimpleUploadedFile('recording.webm', b'test-audio-data', content_type='audio/webm'),
        }, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['content'], '修订后的转写内容')
        self.assertTrue(response.data['audio_file_url'])

    def test_file_extract_word_and_plain_text(self):
        for upload in [word_upload(), SimpleUploadedFile('notes.txt', '中文听课记录'.encode('gb18030'))]:
            response = self.client.post('/api/notes/extract/', {'file': upload}, format='multipart')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(response.data['excerpt'])
            self.assertIn('warnings', response.data)

    @patch('services.review_materials.recognize_images', return_value='照片中的教案正文')
    def test_photo_is_recognized_instead_of_placeholder(self, vision):
        response = self.client.post('/api/notes/extract/', {'file': SimpleUploadedFile('photo.png', image_bytes())})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['excerpt'], '照片中的教案正文')
        vision.assert_called_once()

    @patch('services.review_materials.recognize_images', side_effect=VisionError('识别暂时失败'))
    def test_import_errors_are_explicit_and_do_not_create_notes(self, vision):
        response = self.client.post('/api/notes/extract/', {'file': SimpleUploadedFile('photo.png', image_bytes())})
        self.assertEqual(response.status_code, 502)
        for filename, data in [('broken.pdf', b'bad'), ('empty.txt', b' '), ('large.txt', ('字' * 60001).encode())]:
            response = self.client.post('/api/notes/extract/', {'file': SimpleUploadedFile(filename, data)})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(ResearchNote.objects.count(), 0)

    def test_permissions_and_validation(self):
        note = ResearchNote.objects.create(author=self.user, title='私有笔记', content='正文')
        other = get_user_model().objects.create_user(username='another-teacher')
        self.client.force_authenticate(other)
        url = f'/api/notes/{note.id}/'
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {'content': '修改'}).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        for data in [{'title': '空正文', 'content': ' '}, {'title': '标签', 'content': '正文', 'tags': {'invalid': True}}]:
            self.assertEqual(self.client.post('/api/notes/', data, format='json').status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/notes/extract/', {'file': word_upload()}).status_code, 401)

    def test_list_includes_notes_beyond_twenty(self):
        ResearchNote.objects.bulk_create([ResearchNote(author=self.user, title=f'笔记{i}', content='正文') for i in range(25)])
        response = self.client.get('/api/notes/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 25)

    def test_attachment_type_and_size_validation(self):
        for upload in [SimpleUploadedFile('unsupported.exe', b'x'), SimpleUploadedFile('large.txt', b'x' * (8 * 1024 * 1024 + 1))]:
            response = self.client.post('/api/notes/', {'title': '笔记', 'content': '正文', 'source_file': upload})
            self.assertEqual(response.status_code, 400)
        self.assertFalse(ResearchNote.objects.exists())
