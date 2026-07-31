import json
from .base import BaseConverter
from typing import Dict, Any
from backend.utils.structured_text import build_text_svg, extract_json_texts
from backend.utils.text_utils import read_text_file


class JsonToSvgConverter(BaseConverter):
    """JSON 到 SVG 转换器 - 生成简单的树形可视化"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['svg']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为 SVG 树形图"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 读取JSON文件
            json_data = json.loads(read_text_file(input_path, options.get('encoding')))
            
            self.update_progress(input_path, 30)
            
            svg_content = build_text_svg(
                'JSON Content',
                extract_json_texts(json_data),
                background_color=options.get('background_color', '#ffffff'),
            )
            
            # 写入SVG文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'method': 'json-text-content'
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to SVG conversion failed: {str(e)}")
