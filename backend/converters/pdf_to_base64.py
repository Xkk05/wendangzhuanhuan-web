import base64
import fitz
from .base import BaseConverter
from typing import Dict, Any


class PdfToBase64Converter(BaseConverter):
    """PDF 到 BASE64 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['txt', 'base64']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 PDF 转换为 BASE64 编码"""
        try:
            self.validate_input(input_path)
            
            # 检查是否需要页面提取
            doc = fitz.open(input_path)
            total_pages = doc.page_count
            
            raw_page_range = options.get('pdf_page_range') or options.get('page_range')
            pages = self.parse_page_range(raw_page_range, total_pages=total_pages)
            
            if pages is None:
                # 处理所有页面 - 直接读取文件
                doc.close()
                with open(input_path, 'rb') as f:
                    pdf_data = f.read()
            else:
                # 提取特定页面
                new_doc = fitz.open()
                for page_num in pages:
                    if page_num < 0 or page_num >= total_pages:
                        continue
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                
                doc.close()
                
                if new_doc.page_count == 0:
                     raise Exception("No valid pages selected")
                     
                pdf_data = new_doc.tobytes()
                new_doc.close()
            
            base64_data = base64.b64encode(pdf_data).decode('utf-8')
            
            # 可选：添加 data URI 前缀
            include_prefix = options.get('include_prefix', False)
            if include_prefix:
                base64_data = f"data:application/pdf;base64,{base64_data}"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(base64_data)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"PDF to BASE64 conversion failed: {str(e)}")
