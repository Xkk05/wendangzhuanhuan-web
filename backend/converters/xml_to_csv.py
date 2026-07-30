import csv
import xml.etree.ElementTree as ET
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.structured_data import flatten_xml_values

class XmlToCsvConverter(BaseConverter):
    """XML 到 CSV 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['csv']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 XML 转换为 CSV"""
        try:
            self.validate_input(input_path)
            
            root = ET.parse(input_path).getroot()
            rows = flatten_xml_values(root)
            with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['path', 'value'])
                writer.writerows(rows)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'rows': len(rows)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"XML to CSV conversion failed: {str(e)}")
