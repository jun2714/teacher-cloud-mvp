from docx import Document
from django.test import SimpleTestCase
from services.docx_export import markdown_to_docx


class ExportTableTests(SimpleTestCase):
    def test_continued_data_row_is_not_repeated_as_a_header(self):
        document = Document(markdown_to_docx(
            '|环节|活动|\n|---|---|\n|导入|观察|\n\n'
            '|新知探究|实验与讨论|\n|总结|交流|'))
        self.assertEqual(len(document.tables), 2)
        header, continued = [t.rows[0] for t in document.tables]
        self.assertTrue(header._tr.xpath('./w:trPr/w:tblHeader'))
        self.assertFalse(continued._tr.xpath('./w:trPr/w:tblHeader'))
        self.assertEqual(continued.cells[0].text, '新知探究')
        self.assertFalse(continued.cells[0].paragraphs[0].runs[0].bold)

    def test_separate_markdown_tables_keep_their_real_headers(self):
        document = Document(markdown_to_docx(
            '|环节|活动|\n|---|---|\n|导入|观察|\n\n'
            '|评价|标准|\n|---|---|\n|任务|达成|'))
        self.assertTrue(all(t.rows[0]._tr.xpath('./w:trPr/w:tblHeader') for t in document.tables))
