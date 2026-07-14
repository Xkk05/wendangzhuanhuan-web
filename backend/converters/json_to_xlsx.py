from typing import Dict, Any, List
import json
import os
from .base import BaseConverter
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
            
            # 确保数据是列表形式
            if isinstance(data, dict):
                # 尝试查找列表字段
                list_keys = [k for k, v in data.items() if isinstance(v, list)]
                if len(list_keys) == 1:
                    data = data[list_keys[0]]
                else:
                    data = [data]
            
            if not isinstance(data, list):
                raise ValueError("JSON data must be a list of objects or a single object")
                
            self.update_progress(input_path, 30)
            
            wb = Workbook()
            ws = wb.active
            
            if data:
                # 获取所有键作为表头
                headers = set()
                for item in data:
                    if isinstance(item, dict):
                        headers.update(item.keys())
                
                header_list = sorted(list(headers))
                
                # 写入表头
                ws.append(header_list)
                
                # 写入数据
                row_count = 0
                total_rows = len(data)
                
                for i, item in enumerate(data):
                    row = []
                    if isinstance(item, dict):
                        for header in header_list:
                            # 将非基本类型转换为字符串
                            val = item.get(header, "")
                            if isinstance(val, (dict, list)):
                                val = json.dumps(val, ensure_ascii=False)
                            row.append(val)
                    else:
                        # 简单列表的情况
                        row.append(str(item))
                    
                    ws.append(row)
                    
                    # 进度更新
                    if i % 100 == 0:
                        progress = 30 + int((i / total_rows) * 60)
                        self.update_progress(input_path, progress)
            
            self.update_progress(input_path, 90)
            
            wb.save(output_path)
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to Excel conversion failed: {str(e)}")
