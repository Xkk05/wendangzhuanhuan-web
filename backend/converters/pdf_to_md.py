import fitz  # PyMuPDF
import re
from .base import BaseConverter
from typing import Dict, Any


class PdfToMdConverter(BaseConverter):
    """PDF 到 Markdown 转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加 PyMuPDF markdown 模式（更准确）
    2. 添加表格支持
    3. 添加进度回调
    4. 添加部分失败处理
    5. 保留原有的智能标题识别作为降级方案
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['md', 'markdown']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 PDF 转换为 Markdown（增强版）"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 5)
            
            doc = fitz.open(input_path)
            total_pages = doc.page_count
            
            if total_pages == 0:
                doc.close()
                raise Exception("PDF file is empty")
            
            self.update_progress(input_path, 10)
            
            md_content = []
            failed_pages = []
            use_native_mode = options.get('use_native_mode', True)
            
            # 解析页面范围
            raw_page_range = options.get('pdf_page_range') or options.get('page_range')
            pages = self.parse_page_range(raw_page_range, total_pages=total_pages)
            
            # 确定要处理的页面
            if pages is None:
                pages_to_process = range(total_pages)
            else:
                pages_to_process = pages
            
            processed_count = 0
            total_to_process = len(pages_to_process)
            
            for page_num in pages_to_process:
                if page_num < 0 or page_num >= total_pages:
                    continue
                    
                page = doc.load_page(page_num)
                
                if processed_count > 0:
                    md_content.append('\n---\n')  # 页面分隔符
                
                try:
                    if use_native_mode:
                        # 策略1: 使用 PyMuPDF 的 markdown 模式（更准确）
                        try:
                            text = page.get_text("markdown")
                            if text.strip():
                                md_content.append(text)
                        except ValueError:
                            # markdown 模式失败，降级到智能识别
                            text = self._extract_with_smart_detection(page)
                            md_content.append(text)
                    else:
                        # 策略2: 智能标题识别（原有方案）
                        text = self._extract_with_smart_detection(page)
                        md_content.append(text)
                    
                except Exception as e:
                    print(f"[Page {page_num + 1} failed] {e}")
                    failed_pages.append(page_num + 1)
                    md_content.append(f"\n*[Page {page_num + 1} extraction failed]*\n")
                
                # 更新进度 (10% ~ 85%)
                processed_count += 1
                progress = 10 + int((processed_count / total_to_process) * 75)
                self.update_progress(input_path, progress)
            
            doc.close()
            self.update_progress(input_path, 90)
            
            # 清理多余空行
            result = '\n'.join(md_content)
            result = re.sub(r'\n{3,}', '\n\n', result)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            
            self.update_progress(input_path, 100)
            
            response = {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'total_pages': total_pages
            }
            
            if failed_pages:
                response['partial_failed'] = True
                response['failed_pages'] = failed_pages
                response['warning'] = f"{len(failed_pages)} pages failed to extract"
            
            return response
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"PDF to Markdown conversion failed: {str(e)}")
    
    def _extract_with_smart_detection(self, page) -> str:
        """智能标题识别方案（原有逻辑）"""
        blocks = page.get_text('dict')['blocks']
        content = []
        
        for block in blocks:
            if block['type'] == 0:  # 文本块
                for line in block.get('lines', []):
                    line_text = ''
                    for span in line.get('spans', []):
                        text = span['text']
                        size = span['size']
                        flags = span['flags']
                        
                        # 根据字体大小判断标题级别
                        if size >= 20:
                            text = f"# {text}"
                        elif size >= 16:
                            text = f"## {text}"
                        elif size >= 14:
                            text = f"### {text}"
                        else:
                            # 处理粗体和斜体
                            if flags & 2 ** 4:  # 粗体
                                text = f"**{text}**"
                            if flags & 2 ** 1:  # 斜体
                                text = f"*{text}*"
                        
                        line_text += text
                    
                    if line_text.strip():
                        content.append(line_text)
                
                content.append('')  # 段落间空行
        
        return '\n'.join(content)
