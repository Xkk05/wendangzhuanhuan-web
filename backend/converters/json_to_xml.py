import json
import xml.etree.ElementTree as ET
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.structured_text import extract_json_texts
from backend.utils.text_utils import read_text_file

class JsonToXmlConverter(BaseConverter):
    """JSON 到 XML 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['xml']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为 XML"""
        try:
            self.validate_input(input_path)
            
            data = json.loads(read_text_file(input_path, options.get('encoding')))
            
            # 只导出正文内容，避免把 JSON 字段名、括号和结构代码写进结果。
            root_name = options.get('root_name', 'content')
            root = ET.Element(root_name)
            for text in extract_json_texts(data):
                child = ET.SubElement(root, 'paragraph')
                child.text = text
            
            # 写入 XML 文件
            tree = ET.ElementTree(root)
            # 手动格式化 XML（兼容 Python 3.8，替代 3.9+ 的 ET.indent）
            self._indent_xml(root, level=0)
            tree = ET.ElementTree(root)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
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
            raise Exception(f"JSON to XML conversion failed: {str(e)}")

    def _indent_xml(self, elem, level=0):
        """手动 XML 缩进（兼容 Python 3.6+）"""
        indent = "\n" + "  " * level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            for child in elem:
                self._indent_xml(child, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent
