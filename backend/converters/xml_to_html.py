from .base import BaseConverter
from typing import Dict, Any
import xml.etree.ElementTree as ET
from backend.utils.structured_text import build_text_html, extract_xml_texts

class XmlToHtmlConverter(BaseConverter):
    """XML 到 HTML 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['html']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 XML 正文转换为可阅读的 HTML"""
        try:
            self.validate_input(input_path)
            
            root = ET.parse(input_path).getroot()
            html_content = build_text_html(
                'XML Content',
                extract_xml_texts(root),
                background_color=options.get('background_color', '#ffffff'),
            )
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"XML to HTML conversion failed: {str(e)}")
