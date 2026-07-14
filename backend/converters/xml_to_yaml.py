import yaml
import xmltodict
from .base import BaseConverter
from typing import Dict, Any

class XmlToYamlConverter(BaseConverter):
    """XML 到 YAML 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['yaml', 'yml']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 XML 转换为 YAML"""
        try:
            self.validate_input(input_path)
            
            # 读取 XML 内容
            with open(input_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # 转换为 Python 字典
            data = xmltodict.parse(xml_content)
            
            # 转换为 YAML 并写入文件
            sort_keys = options.get('sort_keys', False)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=sort_keys)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"XML to YAML conversion failed: {str(e)}")
