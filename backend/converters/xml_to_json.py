import json
import xmltodict
from .base import BaseConverter
from typing import Dict, Any

class XmlToJsonConverter(BaseConverter):
    """XML 到 JSON 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['json']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 XML 转换为 JSON"""
        try:
            self.validate_input(input_path)
            
            # 读取 XML 内容
            with open(input_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # 转换为 Python 字典
            data = xmltodict.parse(xml_content)
            
            # 转换为 JSON 并写入文件
            indent = options.get('indent', 2)
            sort_keys = options.get('sort_keys', False)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent, sort_keys=sort_keys)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"XML to JSON conversion failed: {str(e)}")
