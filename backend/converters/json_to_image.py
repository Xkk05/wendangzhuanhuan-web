import json
import os
from .base import BaseConverter
from .json_to_html import JsonToHtmlConverter
from .html_to_image import HtmlToImageConverter
from typing import Dict, Any


class JsonToImageConverter(BaseConverter):
    """JSON 到图片转换器 - 通过HTML中间格式实现"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['png', 'jpg', 'jpeg']
        self.json_to_html = JsonToHtmlConverter()
        self.html_to_image = HtmlToImageConverter()
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为图片（通过HTML中间格式）"""
        temp_html_path = None
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 读取JSON文件
            with open(input_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            self.update_progress(input_path, 20)
            
            # 生成临时HTML文件
            base_dir = os.path.dirname(output_path) or os.getcwd()
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            temp_html_path = os.path.join(base_dir, base_name + "_temp.html")
            
            # 第一步：JSON -> HTML
            self.json_to_html.convert(input_path, temp_html_path, **options)
            self.update_progress(input_path, 50)
            
            # 第二步：HTML -> 图片
            result = self.html_to_image.convert(temp_html_path, output_path, **options)
            self.update_progress(input_path, 100)
            
            result['method'] = 'json->html->image'
            return result
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to Image conversion failed: {str(e)}")
        finally:
            # 清理临时HTML文件
            if temp_html_path and os.path.exists(temp_html_path):
                try:
                    os.remove(temp_html_path)
                except:
                    pass
