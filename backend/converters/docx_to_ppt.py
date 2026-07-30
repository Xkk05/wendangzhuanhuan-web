from typing import Dict, Any
from docx import Document
from docx.table import Table
from pptx import Presentation
from pptx.util import Inches, Pt
from .base import BaseConverter
from backend.utils.docx_content import docx_table_rows, iter_docx_blocks
from backend.utils.pptx_tables import add_paginated_table_slides

class DocxToPptConverter(BaseConverter):
    """Word 转 PPT 转换器"""
    
    def __init__(self):
        super().__init__()

    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        self.validate_input(input_path)
        self.update_progress(input_path, 5)
        
        document = Document(input_path)
        presentation = Presentation()
        presentation.slide_width = Inches(10)
        presentation.slide_height = Inches(7.5)

        for block in iter_docx_blocks(document):
            if isinstance(block, Table):
                add_paginated_table_slides(presentation, 'Document table', docx_table_rows(block))
                continue
            text = block.text.strip()
            if not text:
                continue
            slide = presentation.slides.add_slide(presentation.slide_layouts[1])
            slide.shapes.title.text = text[:80]
            frame = slide.placeholders[1].text_frame
            frame.clear()
            frame.paragraphs[0].text = text
            for paragraph in frame.paragraphs:
                paragraph.font.size = Pt(18)

        if not presentation.slides:
            presentation.slides.add_slide(presentation.slide_layouts[6])
        presentation.save(output_path)
        self.update_progress(input_path, 100)
        return {
            'success': True,
            'output_path': output_path,
            'size': self.get_output_size(output_path),
            'slides': len(presentation.slides),
        }
