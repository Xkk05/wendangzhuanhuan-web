import csv
import re
from .base import BaseConverter
from typing import Dict, Any


class TxtToCsvConverter(BaseConverter):
    """TXT 到 CSV 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['csv']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将文本转换为 CSV"""
        try:
            self.validate_input(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 分隔符选项
            delimiter = options.get('delimiter', None)  # 自动检测或指定
            
            lines = text.strip().split('\n')
            
            # 自动检测分隔符
            if delimiter is None:
                first_line = lines[0] if lines else ''
                if '\t' in first_line:
                    delimiter = '\t'
                elif ';' in first_line:
                    delimiter = ';'
                elif '|' in first_line:
                    delimiter = '|'
                elif ',' in first_line:
                    delimiter = ','
                else:
                    # 使用空格/多空格作为分隔符
                    delimiter = None  # 特殊处理
            
            rows = []
            for line in lines:
                if not line.strip():
                    continue
                
                if delimiter:
                    row = line.split(delimiter)
                else:
                    # 按多个空格分割
                    row = re.split(r'\s{2,}|\t', line)
                
                rows.append([cell.strip() for cell in row])
            
            # 写入 CSV
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'rows': len(rows)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"TXT to CSV conversion failed: {str(e)}")
