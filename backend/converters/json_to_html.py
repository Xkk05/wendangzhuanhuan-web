import json
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.structured_text import build_text_html, extract_json_texts
from backend.utils.text_utils import read_text_file

class JsonToHtmlConverter(BaseConverter):
    """JSON 到 HTML 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['html']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 中的正文文本转换为可阅读的 HTML"""
        try:
            self.validate_input(input_path)
            
            data = json.loads(read_text_file(input_path, options.get('encoding')))
            html_content = build_text_html('JSON Content', extract_json_texts(data))
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to HTML conversion failed: {str(e)}")
