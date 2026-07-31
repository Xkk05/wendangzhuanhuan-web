import base64
import json
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.structured_text import extract_json_texts, extracted_text_document
from backend.utils.text_utils import read_text_file


class JsonToBase64Converter(BaseConverter):
    """JSON 到 BASE64 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['txt', 'base64']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为 BASE64 编码"""
        try:
            self.validate_input(input_path)
            
            data = json.loads(read_text_file(input_path, options.get('encoding')))
            json_data = extracted_text_document(extract_json_texts(data)).encode('utf-8')
            
            base64_data = base64.b64encode(json_data).decode('utf-8')
            
            include_prefix = options.get('include_prefix', False)
            if include_prefix:
                base64_data = f"data:text/plain;charset=utf-8;base64,{base64_data}"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(base64_data)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to BASE64 conversion failed: {str(e)}")
