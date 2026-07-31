from __future__ import annotations

import html

from docx.document import Document as DocumentType
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P


def iter_docx_blocks(document: DocumentType):
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def docx_table_rows(table: Table) -> list[list[str]]:
    return [[cell.text.strip() for cell in row.cells] for row in table.rows]


def docx_table_to_html(table: Table) -> str:
    rows = docx_table_rows(table)
    if not rows:
        return ""
    body = []
    for row_index, row in enumerate(rows):
        cell_tag = "th" if row_index == 0 else "td"
        cells = "".join(f"<{cell_tag}>{html.escape(value)}</{cell_tag}>" for value in row)
        body.append(f"<tr>{cells}</tr>")
    return f"<table>{''.join(body)}</table>"


def docx_paragraph_images(paragraph: Paragraph) -> list[dict[str, object]]:
    images = []
    seen_relationships = set()
    for blip in paragraph._element.findall(
        './/{http://schemas.openxmlformats.org/drawingml/2006/main}blip'
    ):
        relationship_id = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
        if not relationship_id or relationship_id in seen_relationships:
            continue
        seen_relationships.add(relationship_id)
        image_part = paragraph.part.related_parts.get(relationship_id)
        if not image_part:
            continue
        images.append({
            'blob': image_part.blob,
            'content_type': getattr(image_part, 'content_type', ''),
        })
    return images
