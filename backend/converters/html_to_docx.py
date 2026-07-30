from docx import Document
from docx.shared import Pt
from bs4 import NavigableString, Tag
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.html_content import prepare_content_soup
from backend.utils.text_utils import read_text_file


class HtmlToDocxConverter(BaseConverter):
    """HTML 到 DOCX 转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加进度回调
    2. 支持两种模式：源码模式 / 文本提取模式
    3. 更好的文本清理
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['docx', 'doc']

    @staticmethod
    def _table_rows(table_element: Tag) -> list[list[str]]:
        rows = []
        for row in table_element.find_all('tr'):
            if row.find_parent('table') is not table_element:
                continue
            cells = [cell.get_text(' ', strip=True) for cell in row.find_all(['th', 'td'], recursive=False)]
            if cells:
                rows.append(cells)
        return rows

    def _render_table(self, doc: Document, element: Tag) -> None:
        rows = self._table_rows(element)
        column_count = max((len(row) for row in rows), default=0)
        if not rows or not column_count:
            return
        table = doc.add_table(rows=len(rows), cols=column_count)
        table.style = 'Table Grid'
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                table.cell(row_index, column_index).text = value

    def _render_list(self, doc: Document, element: Tag) -> None:
        style = 'List Bullet' if element.name == 'ul' else 'List Number'
        for item in element.find_all('li', recursive=False):
            text_parts = []
            nested_lists = []
            for child in item.children:
                if isinstance(child, NavigableString):
                    text_parts.append(str(child).strip())
                elif isinstance(child, Tag) and child.name in {'ul', 'ol'}:
                    nested_lists.append(child)
                elif isinstance(child, Tag):
                    text_parts.append(child.get_text(' ', strip=True))
            text = ' '.join(part for part in text_parts if part).strip()
            if text:
                doc.add_paragraph(text, style=style)
            for nested_list in nested_lists:
                self._render_list(doc, nested_list)

    def _render_blocks(self, doc: Document, parent: Tag) -> None:
        for element in parent.children:
            if isinstance(element, NavigableString):
                text = str(element).strip()
                if text:
                    doc.add_paragraph(text)
                continue
            if not isinstance(element, Tag):
                continue

            if element.name in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
                doc.add_heading(element.get_text(' ', strip=True), level=int(element.name[1]))
            elif element.name == 'table':
                self._render_table(doc, element)
            elif element.name in {'ul', 'ol'}:
                self._render_list(doc, element)
            elif element.name in {'p', 'pre', 'blockquote'}:
                text = element.get_text(' ', strip=True)
                if text:
                    doc.add_paragraph(text)
            elif element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'pre', 'blockquote', 'table', 'ul', 'ol']):
                self._render_blocks(doc, element)
            else:
                text = element.get_text(' ', strip=True)
                if text:
                    doc.add_paragraph(text)
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 HTML 转换为 DOCX"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 获取选项
            mode = options.get('mode', 'text')  # 'source' or 'text'
            
            # 读取 HTML
            html_content = read_text_file(input_path, options.get('encoding'))
            
            self.update_progress(input_path, 30)
            
            # 创建 Word 文档
            doc = Document()
            
            if mode == 'source':
                # 源码模式：保留完整 HTML 源码
                paragraph = doc.add_paragraph()
                run = paragraph.add_run(html_content)
                run.font.name = 'Consolas'
                run.font.size = Pt(10)
            else:
                soup = prepare_content_soup(html_content, options)
                self.update_progress(input_path, 50)
                root = soup.body or soup
                self._render_blocks(doc, root)
                self.update_progress(input_path, 80)
            
            # 保存文档
            doc.save(output_path)
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'mode': mode
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"HTML to DOCX conversion failed: {str(e)}")
