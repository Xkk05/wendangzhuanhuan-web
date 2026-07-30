from __future__ import annotations

from math import ceil

from pptx.util import Inches, Pt


def add_paginated_table_slides(
    presentation,
    title: str,
    rows: list[list[str]],
    max_rows: int = 14,
    max_columns: int = 8,
) -> int:
    if not rows or not any(any(str(value).strip() for value in row) for row in rows):
        return 0

    column_count = max(len(row) for row in rows)
    normalized_rows = [list(map(str, row)) + [""] * (column_count - len(row)) for row in rows]
    header = normalized_rows[0]
    data_rows = normalized_rows[1:]
    row_chunks = [data_rows[index:index + max_rows - 1] for index in range(0, len(data_rows), max_rows - 1)] or [[]]
    column_chunks = [list(range(index, min(index + max_columns, column_count))) for index in range(0, column_count, max_columns)]

    slide_count = 0
    total_pages = len(row_chunks) * len(column_chunks)
    for row_chunk in row_chunks:
        for columns in column_chunks:
            slide_count += 1
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            title_box = slide.shapes.add_textbox(Inches(0.45), Inches(0.22), Inches(9.1), Inches(0.55))
            title_paragraph = title_box.text_frame.paragraphs[0]
            title_paragraph.text = title if total_pages == 1 else f"{title} ({slide_count}/{total_pages})"
            title_paragraph.font.size = Pt(20)
            title_paragraph.font.bold = True

            page_rows = [header] + row_chunk
            table_shape = slide.shapes.add_table(
                len(page_rows), len(columns), Inches(0.45), Inches(0.95), Inches(9.1), Inches(5.95)
            )
            table = table_shape.table
            font_size = 10 if len(columns) <= 6 else 8
            for row_index, row in enumerate(page_rows):
                for page_column, source_column in enumerate(columns):
                    cell = table.cell(row_index, page_column)
                    cell.text = row[source_column]
                    cell.text_frame.word_wrap = True
                    for paragraph in cell.text_frame.paragraphs:
                        for run in paragraph.runs:
                            run.font.size = Pt(font_size)
                            run.font.bold = row_index == 0
    return slide_count
