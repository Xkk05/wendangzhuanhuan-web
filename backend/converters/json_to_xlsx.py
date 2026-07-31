from typing import Dict, Any
import json
from .base import BaseConverter
from backend.utils.structured_text import extract_json_texts
from backend.utils.text_utils import read_text_file
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
            data = json.loads(read_text_file(input_path, options.get('encoding')))
            
            self.update_progress(input_path, 30)
            wb = Workbook()
            ws = wb.active
            ws.title = 'Content'
            ws.append(['内容'])
            for value in extract_json_texts(data):
                ws.append([value])
            row_count = ws.max_row
            ws.column_dimensions['A'].width = 64
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
