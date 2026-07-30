import os
from .base import BaseConverter
from .html_to_pdf import HtmlToPdfConverter
from .json_to_html import JsonToHtmlConverter
from typing import Dict, Any


class JsonToPdfConverter(BaseConverter):
    """JSON 到 PDF 转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加进度回调
    2. 支持多种显示模式（树形/代码）
    3. 更好的格式化和语法高亮
    4. 错误处理增强
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['pdf']
        self.html_converter = HtmlToPdfConverter()
        self.json_to_html = JsonToHtmlConverter()
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为 PDF（增强版）"""
        temp_html_path = None
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            base_dir = os.path.dirname(output_path) or os.getcwd()
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            temp_html_path = os.path.join(base_dir, base_name + "_temp.html")
            self.json_to_html.convert(input_path, temp_html_path, **options)
            
            self.update_progress(input_path, 60)
            
            # 转换为 PDF
            result = self.html_converter.convert(temp_html_path, output_path, **options)
            self.update_progress(input_path, 100)
            
            result['mode'] = 'text'
            return result
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to PDF conversion failed: {str(e)}")
        finally:
            if temp_html_path and os.path.exists(temp_html_path):
                try:
                    os.remove(temp_html_path)
                except:
                    pass
