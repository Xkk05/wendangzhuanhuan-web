import json
import yaml
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.structured_text import extract_json_texts
from backend.utils.text_utils import read_text_file

class JsonToYamlConverter(BaseConverter):
    """JSON 到 YAML 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['yaml', 'yml']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为 YAML"""
        try:
            self.validate_input(input_path)
            
            data = json.loads(read_text_file(input_path, options.get('encoding')))
            
            # 转换参数
            indent = options.get('indent', 2)
            sort_keys = options.get('sort_keys', False)
            
            content = extract_json_texts(data)
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    content,
                    f, 
                    indent=indent, 
                    sort_keys=sort_keys, 
                    allow_unicode=True,
                    default_flow_style=False
                )
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except json.JSONDecodeError as e:
            self.cleanup_on_error(output_path)
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to YAML conversion failed: {str(e)}")
