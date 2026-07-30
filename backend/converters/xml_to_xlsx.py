import xml.etree.ElementTree as ET
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.structured_data import append_path_value_rows, flatten_xml_values


class XmlToXlsxConverter(BaseConverter):
    """XML 到 XLSX 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['xlsx']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 XML 转换为 XLSX"""
        try:
            self.validate_input(input_path)
            
            # 尝试导入 openpyxl
            try:
                from openpyxl import Workbook
            except ImportError:
                raise Exception("需要安装 openpyxl: pip install openpyxl")
            
            tree = ET.parse(input_path)
            root = tree.getroot()
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Data"
            row_count = append_path_value_rows(ws, flatten_xml_values(root))
            ws.column_dimensions['A'].width = 48
            ws.column_dimensions['B'].width = 36
            wb.save(output_path)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'rows': row_count
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"XML to XLSX conversion failed: {str(e)}")
