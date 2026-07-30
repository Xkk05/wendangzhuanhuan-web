from typing import Dict, Any, List
import json
from .base import BaseConverter
from backend.utils.structured_data import append_path_value_rows, flatten_json_values
try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

class JsonToXlsxConverter(BaseConverter):
    """JSON 转 Excel (XLSX) 转换器"""
    
    def __init__(self):
        super().__init__()
        
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        if Workbook is None:
            raise ImportError("openpyxl library is required for JSON to Excel conversion")
            
        self.validate_input(input_path)
        self.update_progress(input_path, 10)
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.update_progress(input_path, 30)
            wb = Workbook()
            ws = wb.active
            ws.title = 'Data'
            row_count = append_path_value_rows(ws, flatten_json_values(data))
            ws.column_dimensions['A'].width = 48
            ws.column_dimensions['B'].width = 36
            self.update_progress(input_path, 90)
            
            wb.save(output_path)
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'rows': row_count
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to Excel conversion failed: {str(e)}")
