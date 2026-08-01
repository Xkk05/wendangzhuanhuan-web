from __future__ import annotations

from typing import Optional

from docx.document import Document as DocumentObject
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def normalize_document_for_portrait_pdf(document: DocumentObject) -> bool:
    """Prepare a DOCX for portrait PDF export without clipping wide content."""
    changed = _normalize_sections_to_portrait(document)
    changed = _fit_tables_to_page_width(document) or changed
    return changed


def _normalize_sections_to_portrait(document: DocumentObject) -> bool:
    changed = False
    for section in document.sections:
        if section.orientation != WD_ORIENT.PORTRAIT:
            section.orientation = WD_ORIENT.PORTRAIT
            changed = True
        if section.page_width > section.page_height:
            section.page_width, section.page_height = section.page_height, section.page_width
            changed = True
    return changed


def _fit_tables_to_page_width(document: DocumentObject) -> bool:
    changed = False
    available_width = _min_available_page_width(document)
    for table in document.tables:
        table.autofit = True
        _set_table_width_percent(table, 5000)
        _set_table_layout_autofit(table)
        if available_width:
            _scale_cell_widths(table, available_width)
        changed = True
    return changed


def _min_available_page_width(document: DocumentObject) -> Optional[int]:
    widths = []
    for section in document.sections:
        page_width = int(section.page_width or 0)
        margins = int(section.left_margin or 0) + int(section.right_margin or 0)
        available = page_width - margins
        if available > 0:
            widths.append(available)
    return min(widths) if widths else None


def _set_table_width_percent(table, width: int) -> None:
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.insert(0, tbl_w)
    tbl_w.set(qn("w:type"), "pct")
    tbl_w.set(qn("w:w"), str(width))


def _set_table_layout_autofit(table) -> None:
    tbl_pr = table._tbl.tblPr
    tbl_layout = tbl_pr.find(qn("w:tblLayout"))
    if tbl_layout is None:
        tbl_layout = OxmlElement("w:tblLayout")
        tbl_pr.append(tbl_layout)
    tbl_layout.set(qn("w:type"), "autofit")


def _scale_cell_widths(table, available_width: int) -> None:
    if not table.rows:
        return

    first_row_widths = [int(cell.width or 0) for cell in table.rows[0].cells]
    total_width = sum(width for width in first_row_widths if width > 0)
    if total_width <= available_width or total_width <= 0:
        return

    scale = available_width / total_width
    for row in table.rows:
        for cell in row.cells:
            width = int(cell.width or 0)
            if width > 0:
                cell.width = max(1, int(width * scale))
