import xmltodict
import csv
from .base import BaseConverter
from typing import Dict, Any

class XmlToCsvConverter(BaseConverter):
    """XML 到 CSV 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['csv']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 XML 转换为 CSV"""
        try:
            self.validate_input(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            data = xmltodict.parse(xml_content)
            
            # 尝试展平结构，找到列表数据
            # 这是一个简单的启发式方法，寻找第一个列表节点
            rows = []
            
            def find_list(d):
                for k, v in d.items():
                    if isinstance(v, list):
                        return v
                    if isinstance(v, dict):
                        res = find_list(v)
                        if res: return res
                return None
            
            found_list = find_list(data)
            
            if found_list:
                rows = found_list
            else:
                # 尝试将整个结构视为单行（如果不是太复杂）
                # 这里简化处理：如果没有找到列表，就抛出错误或尝试转换根节点
                # 实际生产中可能需要更复杂的展平逻辑
                # 暂时将根元素的子元素作为一行
                root_key = list(data.keys())[0]
                root_val = data[root_key]
                if isinstance(root_val, dict):
                    rows = [root_val]
                else:
                    raise ValueError("Could not extract tabular data from XML")

            if not rows:
                with open(output_path, 'w', encoding='utf-8', newline='') as f:
                    pass
                return {'success': True, 'output_path': output_path, 'size': 0}

            # 提取表头
            headers = set()
            for item in rows:
                if isinstance(item, dict):
                    headers.update(item.keys())
            
            fieldnames = sorted(list(headers))
            
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for item in rows:
                    if isinstance(item, dict):
                        # xmltodict 解析的值可能是 OrderedDict 或包含 @ 属性
                        # 这里简单处理，直接写入
                        # 如果值是字典（嵌套结构），可能需要进一步处理，这里直接转字符串
                        row_to_write = {}
                        for k, v in item.items():
                            if isinstance(v, (dict, list)):
                                row_to_write[k] = str(v)
                            else:
                                row_to_write[k] = v
                        writer.writerow(row_to_write)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"XML to CSV conversion failed: {str(e)}")
