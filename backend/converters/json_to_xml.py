import json
import xml.etree.ElementTree as ET
from .base import BaseConverter
from typing import Dict, Any

class JsonToXmlConverter(BaseConverter):
    """JSON 到 XML 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['xml']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为 XML"""
        try:
            self.validate_input(input_path)
            
            # 读取 JSON 内容
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换为 XML
            root_name = options.get('root_name', 'root')
            root = ET.Element(root_name)
            self._build_xml(root, data)
            
            # 写入 XML 文件
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ", level=0) # 格式化 XML
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

    def _build_xml(self, parent, data):
        """递归构建 XML 结构"""
        if isinstance(data, dict):
            for key, value in data.items():
                # 处理非法字符或数字开头的 key
                tag_name = str(key)
                if not tag_name[0].isalpha() and tag_name[0] != '_':
                    tag_name = f"item_{tag_name}"
                
                child = ET.SubElement(parent, tag_name)
                self._build_xml(child, value)
        elif isinstance(data, list):
            for item in data:
                child = ET.SubElement(parent, "item")
                self._build_xml(child, item)
        else:
            parent.text = str(data)
