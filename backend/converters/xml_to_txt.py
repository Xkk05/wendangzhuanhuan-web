import xml.etree.ElementTree as ET
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.structured_text import extract_xml_texts


class XmlToTxtConverter(BaseConverter):
    """XML 到 TXT 转换器 - 提取所有文本内容"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['txt']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 XML 转换为 TXT"""
        try:
            self.validate_input(input_path)
            
            tree = ET.parse(input_path)
            root = tree.getroot()
            
            text_content = '\n\n'.join(extract_xml_texts(root))
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"XML to TXT conversion failed: {str(e)}")
