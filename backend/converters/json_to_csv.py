import json
import csv
from .base import BaseConverter
from typing import Dict, Any, List

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
            
            # 确保数据是列表形式，如果不是，尝试转换
            if isinstance(data, dict):
                # 尝试查找列表字段
                list_keys = [k for k, v in data.items() if isinstance(v, list)]
                if len(list_keys) == 1:
                    data = data[list_keys[0]]
                else:
                    # 单个对象转为单行 CSV
                    data = [data]
            
            if not isinstance(data, list):
                raise ValueError("JSON data must be a list of objects or a single object")
            
            if not data:
                # 空列表，创建一个空文件
                with open(output_path, 'w', encoding='utf-8', newline='') as f:
                    pass
                return {'success': True, 'output_path': output_path, 'size': 0}

            # 获取所有可能的键（表头）
            headers = set()
            for item in data:
                if isinstance(item, dict):
                    headers.update(item.keys())
            
            fieldnames = sorted(list(headers))
            
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for item in data:
                    if isinstance(item, dict):
                        writer.writerow(item)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to CSV conversion failed: {str(e)}")
