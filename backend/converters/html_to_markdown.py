try:
    from markdownify import markdownify
except ImportError:
    markdownify = None
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.html_content import prepare_content_soup
from backend.utils.text_utils import read_text_file


class HtmlToMarkdownConverter(BaseConverter):
    """HTML 到 Markdown 转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加进度回调
    2. 支持两种模式：源码模式 / 文本提取模式
    3. 基础的 HTML 到 Markdown 转换
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['md', 'markdown']

    def _fallback_markdown(self, soup) -> str:
        lines = []
        for element in (soup.body or soup).find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'table']):
            if element.find_parent(['table', 'ul', 'ol']) and element.name != 'table':
                continue
            text = element.get_text(' ', strip=True)
            if not text:
                continue
            if element.name.startswith('h'):
                lines.append(f"{'#' * int(element.name[1])} {text}")
            elif element.name == 'p':
                lines.append(text)
            elif element.name in {'ul', 'ol'}:
                for index, item in enumerate(element.find_all('li', recursive=False), start=1):
                    prefix = '-' if element.name == 'ul' else f'{index}.'
                    lines.append(f"{prefix} {item.get_text(' ', strip=True)}")
            elif element.name == 'table':
                rows = [[cell.get_text(' ', strip=True) for cell in row.find_all(['th', 'td'])] for row in element.find_all('tr')]
                if rows:
                    width = max(len(row) for row in rows)
                    rows = [row + [''] * (width - len(row)) for row in rows]
                    lines.append('| ' + ' | '.join(rows[0]) + ' |')
                    lines.append('| ' + ' | '.join(['---'] * width) + ' |')
                    lines.extend('| ' + ' | '.join(row) + ' |' for row in rows[1:])
        return '\n\n'.join(lines)
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 HTML 转换为 Markdown"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 获取选项
            mode = options.get('mode', 'text')  # 'source' or 'text'
            
            html_content = read_text_file(input_path, options.get('encoding'))
            
            self.update_progress(input_path, 30)
            
            if mode == 'source':
                # 源码模式：直接复制 HTML 源码
                output_content = html_content
            else:
                soup = prepare_content_soup(html_content, options)
                self.update_progress(input_path, 50)
                if markdownify:
                    output_content = markdownify(str(soup.body or soup), heading_style='ATX').strip() + '\n'
                else:
                    output_content = self._fallback_markdown(soup).strip() + '\n'
                self.update_progress(input_path, 80)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'mode': mode
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"HTML to Markdown conversion failed: {str(e)}")
