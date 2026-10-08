"""Prepare cover/content artwork from the four supplied PPTX files.

Usage: python scripts/prepare_lesson_templates.py <source-directory> <output-directory>
The originals are read only. Render the two-slide copies with render_lesson_templates.mjs.
"""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET

TEMPLATES = {
    'education-grey': '灰色简约教育通用.pptx',
    'research-purple': '紫色教研培训报演示模板.pptx',
    'training-orange': '橙黄扁平简约教育培训模版.pptx',
    'teacher-grey': '灰色简约教师述职演示模板.pptx',
}
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')


def prepare(source, output):
    output.mkdir(parents=True, exist_ok=True)
    for key, filename in TEMPLATES.items():
        with ZipFile(source / filename) as original, ZipFile(output / (key + '.pptx'), 'w', ZIP_DEFLATED) as target:
            for entry in original.infolist():
                data = original.read(entry.filename)
                if entry.filename == 'ppt/presentation.xml':
                    root = ET.fromstring(data)
                    ids = root.find('p:sldIdLst', NS)
                    for index, slide_id in enumerate(list(ids)):
                        if index not in (0, 3):
                            ids.remove(slide_id)
                    data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
                elif entry.filename in ('ppt/slides/slide1.xml', 'ppt/slides/slide4.xml'):
                    root = ET.fromstring(data)
                    tree = root.find('p:cSld/p:spTree', NS)
                    for shape in list(tree):
                        if shape.tag in (f"{{{NS['p']}}}nvGrpSpPr", f"{{{NS['p']}}}grpSpPr"):
                            continue
                        # Keep the supplied chapter marker; all sample content is removed.
                        name = shape.find('.//p:cNvPr', NS)
                        marker = entry.filename.endswith('slide4.xml') and name is not None and name.get('name', '').startswith('Freeform')
                        if not marker:
                            tree.remove(shape)
                    data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
                target.writestr(entry, data)
        print(key)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)
