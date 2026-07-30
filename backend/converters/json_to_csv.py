import json
import csv
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.structured_data import flatten_json_values

class JsonToCsvConverter(BaseConverter):
    """JSON 到 CSV 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['csv']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为 CSV"""
        try:
            self.validate_input(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            rows = flatten_json_values(data)
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
            raise Exception(f"JSON to CSV conversion failed: {str(e)}")
