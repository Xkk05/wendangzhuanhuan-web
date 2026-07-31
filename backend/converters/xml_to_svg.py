import xml.etree.ElementTree as ET
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.structured_text import build_text_svg, extract_xml_texts


class XmlToSvgConverter(BaseConverter):
    """XML 到 SVG 转换器 - 支持SVG格式的XML文件"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['svg']
    
    def _is_svg_xml(self, root) -> bool:
        """检查XML是否是SVG格式"""
        # 检查根元素是否是svg
        tag = root.tag.lower()
        if '}' in tag:
            # 处理命名空间
            tag = tag.split('}')[1]
        
        return tag == 'svg'
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 XML 转换为 SVG"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 解析XML
            tree = ET.parse(input_path)
            root = tree.getroot()
            
            self.update_progress(input_path, 30)
            
            # 检查是否是SVG格式的XML
            if self._is_svg_xml(root):
                # 直接复制SVG内容
                with open(input_path, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                method = 'svg-xml-copy'
            else:
                svg_content = build_text_svg(
                    'XML Content',
                    extract_xml_texts(root),
                    background_color=options.get('background_color', '#ffffff'),
                )
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                method = 'xml-text-content'
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'method': method
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"XML to SVG conversion failed: {str(e)}")
