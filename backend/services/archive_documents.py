"""Print-ready Word tables for archive data and document indexes."""
from io import BytesIO
from copy import deepcopy
import re

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor


def _value(value):
    # Treat source values as literal text, never Word fields, HTML or Markdown.
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', '' if value is None else str(value))


def _font(run, size=10, bold=False, heading=False):
    run.font.name = '微软雅黑'
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0x1A, 0x5F, 0xB4) if heading else RGBColor(0x2A, 0x31, 0x40)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), '微软雅黑')


def print_tables(title, sections, *, metadata=(), note=''):
    """sections: (heading, header row, data rows, relative column widths)."""
    doc = Document()
    page = doc.sections[0]
    page.page_width, page.page_height = Mm(210), Mm(297)
    page.top_margin, page.bottom_margin = Mm(24), Mm(24)
    page.left_margin = page.right_margin = Mm(22)
    page.footer_distance = Mm(9)
    usable = page.page_width - page.left_margin - page.right_margin
    normal = doc.styles['Normal']
    normal.font.name, normal.font.size = '微软雅黑', Pt(10)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.15
    p = doc.add_paragraph(style='Title')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    _font(p.add_run(_value(title)), 18, True, True)
    for label, value in metadata:
        p = doc.add_paragraph()
        _font(p.add_run(_value(label) + '：'), 10, True)
        _font(p.add_run(_value(value)), 10)
    if note:
        _font(doc.add_paragraph().add_run(_value(note)), 10)

    for heading, headers, rows, weights in sections:
        if heading:
            p = doc.add_paragraph()
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(10)
            _font(p.add_run(_value(heading)), 12, True, True)
        if not rows:
            _font(doc.add_paragraph().add_run('当前范围暂无记录。'))
            continue
        if len(weights) != len(headers) or any(len(row) != len(headers) for row in rows):
            raise ValueError('Table columns do not match the declared headings.')
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        table.autofit = False
        widths = [int(usable * weight / sum(weights)) for weight in weights]
        for col, width in zip(table.columns, widths):
            col.width = width
        header = OxmlElement('w:tblHeader')
        table.rows[0]._tr.get_or_add_trPr().append(header)
        for index, values in enumerate([headers, *rows]):
            row = table.rows[0] if index == 0 else table.add_row()
            if all(len(_value(value)) < 240 for value in values):
                row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
            for cell, value, width in zip(row.cells, values, widths):
                cell.width = width
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                properties = cell._tc.get_or_add_tcPr()
                margins = OxmlElement('w:tcMar')
                for side in ('top', 'bottom', 'left', 'right'):
                    item = OxmlElement('w:' + side)
                    item.set(qn('w:w'), '65' if side in ('top', 'bottom') else '80')
                    item.set(qn('w:type'), 'dxa')
                    margins.append(item)
                properties.append(margins)
                if index == 0:
                    shading = OxmlElement('w:shd')
                    shading.set(qn('w:fill'), 'E8F1FF')
                    properties.append(shading)
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.15
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if index == 0 or isinstance(value, (int, float)) else WD_ALIGN_PARAGRAPH.LEFT
                _font(p.add_run(_value(value)), 10, index == 0)
        doc.add_paragraph().paragraph_format.space_after = Pt(0)

    _page_numbers(doc)
    output = BytesIO()
    doc.save(output)
    return output.getvalue()


def _page_numbers(doc):
    page = doc.sections[0]
    page.footer_distance = Mm(9)
    footer = page.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(footer.add_run('第 '), 9)
    for field, suffix in [('PAGE', ' 页 / 共 '), ('NUMPAGES', ' 页')]:
        element = OxmlElement('w:fldSimple')
        element.set(qn('w:instr'), field)
        footer._p.append(element)
        _font(footer.add_run(suffix), 9)


def collected_documents(title, introduction, documents):
    """One teacher's complete materials, with each source starting on a new page."""
    from services.docx_export import markdown_to_docx

    doc = Document(markdown_to_docx('# ' + title + '\n\n' + introduction, background=False))
    for heading, body in documents:
        part = Document(markdown_to_docx('# ' + heading + '\n\n' + body, background=False))
        doc.add_page_break()
        # This renderer emits text/tables only when background=False; it has no
        # media/hyperlink relationships that would need remapping between files.
        for element in part.element.body:
            if element.tag != qn('w:sectPr'):
                doc.element.body.insert(-1, deepcopy(element))
    _page_numbers(doc)
    output = BytesIO()
    doc.save(output)
    return output.getvalue()


def roster_sections(rows):
    """Keep all 12 roster fields in portrait tables joined by teacher number."""
    columns = [(0, 1, 2, 3, 4), (0, 1, 5, 6, 9), (0, 1, 7, 8), (0, 1, 10, 11)]
    titles = ['注册与入选依据', '成果与活动记录', '使用时间记录', '跨批使用与名单线索']
    weights = [(1, 1.4, 2.3, 2.4, 3), (1, 1.4, 2, 2, 2), (1, 1.4, 3, 3), (1, 1.4, 3, 3)]
    return [(title, [rows[0][i] for i in cols], [[r[i] for i in cols] for r in rows[1:]
              if title != titles[-1] or r[10] or r[11]], width)
            for title, cols, width in zip(titles, columns, weights)]


def index_sections(rows, kind='records'):
    """A readable catalog plus file lookup; no narrow columns with long paths."""
    if kind == 'personal':
        overview = [[r[0], r[1], r[2], r[3], r[4]] for r in rows[1:]]
        lookup = [[r[0], r[1], r[5]] for r in rows[1:]]
        return [('报告目录', rows[0][:5], overview, (1, 1.5, 2.5, 1.5, 3)),
                ('文件位置索引', ['教师编号', '姓名', '文件名'], lookup, (1, 1.5, 7))]
    overview = [[f'{r[1]} #{r[0]}', r[2], r[3], f'{r[4]}\n{r[6]}'] for r in rows[1:]]
    lookup = [[f'{r[1]} #{r[0]}', r[2], r[5]] for r in rows[1:]]
    return [('资料目录', ['来源编号', '教师', '标题', '时间与正文状态'], overview, (1.5, 1.5, 4.5, 2.5)),
            ('文件位置索引', ['来源编号', '教师', '文件名'], lookup, (1.5, 1.5, 7))]
