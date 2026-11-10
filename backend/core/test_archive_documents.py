from io import BytesIO

from django.test import SimpleTestCase
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Mm

from services.archive_documents import print_tables, roster_sections


class ArchivePrintTests(SimpleTestCase):
    def test_a4_portrait_tables_are_editable_and_have_repeated_headers_and_page_numbers(self):
        rows = [['教师', '=原文*内容*\n包含换行和长文件名.docx'], ['另一个教师', '<内容>&特殊字符']]
        data = print_tables('过程数据', [('记录明细', ['姓名', '内容'], rows, (1, 3))], metadata=[('批次', '第一批')])
        doc = Document(BytesIO(data))
        self.assertAlmostEqual(doc.sections[0].page_width / Mm(1), 210, places=1)
        self.assertLess(doc.sections[0].page_width, doc.sections[0].page_height)
        self.assertEqual(doc.tables[0].cell(1, 1).text, rows[0][1])
        self.assertEqual(doc.tables[0].cell(2, 1).text, rows[1][1])
        self.assertIsNotNone(doc.tables[0].rows[0]._tr.find(qn('w:trPr')).find(qn('w:tblHeader')))
        self.assertIn('NUMPAGES', doc.sections[0].footer._element.xml)
        self.assertFalse(doc.inline_shapes)
        self.assertGreater(doc.tables[0].columns[1].width, doc.tables[0].columns[0].width)

    def test_roster_retains_all_columns_in_readable_tables(self):
        headers = [f'列{i}' for i in range(12)]
        row = [f'值{i}' for i in range(12)]
        sections = roster_sections([headers, row])
        self.assertTrue(all(len(s[1]) <= 5 for s in sections))
        values = {v for s in sections for r in s[2] for v in r}
        self.assertEqual(values, set(row))

    def test_empty_section_is_explained_without_fake_records(self):
        doc = Document(BytesIO(print_tables('空范围', [('过程记录', ['标题'], [], (1,))])))
        self.assertIn('当前范围暂无记录。', [p.text for p in doc.paragraphs])
        self.assertFalse(doc.tables)
