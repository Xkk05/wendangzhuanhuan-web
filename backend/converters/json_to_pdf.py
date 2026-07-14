import json
import os
from .base import BaseConverter
from .html_to_pdf import HtmlToPdfConverter
from typing import Dict, Any


class JsonToPdfConverter(BaseConverter):
    """JSON 到 PDF 转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加进度回调
    2. 支持多种显示模式（树形/代码）
    3. 更好的格式化和语法高亮
    4. 错误处理增强
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['pdf']
        self.html_converter = HtmlToPdfConverter()
    
    def _json_to_html(self, data, depth=0) -> str:
        """将 JSON 数据转换为 HTML"""
        indent = '  ' * depth
        
        if isinstance(data, dict):
            items = []
            for key, value in data.items():
                items.append(f'<li><strong>{key}:</strong> {self._json_to_html(value, depth + 1)}</li>')
            return f'<ul style="list-style-type: none; padding-left: 20px;">{"".join(items)}</ul>'
        
        elif isinstance(data, list):
            items = []
            for i, item in enumerate(data):
                items.append(f'<li><span style="color: #666;">[{i}]</span> {self._json_to_html(item, depth + 1)}</li>')
            return f'<ol style="padding-left: 20px;">{"".join(items)}</ol>'
        
        elif isinstance(data, str):
            return f'<span style="color: #008000;">"{data}"</span>'
        
        elif isinstance(data, bool):
            return f'<span style="color: #0000ff;">{str(data).lower()}</span>'
        
        elif isinstance(data, (int, float)):
            return f'<span style="color: #ff6600;">{data}</span>'
        
        elif data is None:
            return '<span style="color: #999;">null</span>'
        
        return str(data)
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为 PDF（增强版）"""
        temp_html_path = None
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 获取选项
            mode = options.get('mode', 'tree')  # 'tree' or 'code'
            indent = options.get('indent', 2)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.update_progress(input_path, 30)
            
            # 生成 HTML
            if mode == 'code':
                # 代码模式：格式化的 JSON 代码
                json_str = json.dumps(data, indent=indent, ensure_ascii=False)
                json_html = f'<pre style="background:#f5f5f5;padding:15px;border-radius:5px;overflow-x:auto;">{json_str}</pre>'
            else:
                # 树形模式：结构化展示
                json_html = self._json_to_html(data)
            
            html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>JSON Document</title>
    <style>
        body {{
            font-family: "Microsoft YaHei", "SimSun", monospace;
            background-color: #ffffff;
            color: #333;
            padding: 20px;
            line-height: 1.6;
        }}
        ul, ol {{ margin: 5px 0; }}
        li {{ margin: 3px 0; }}
        pre {{ 
            font-family: "Consolas", "Courier New", monospace;
            font-size: 12px;
            line-height: 1.4;
        }}
    </style>
</head>
<body>
    <h2>JSON Content</h2>
    {json_html}
</body>
</html>'''
            
            self.update_progress(input_path, 50)
            
            # 保存临时 HTML
            base_dir = os.path.dirname(output_path) or os.getcwd()
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            temp_html_path = os.path.join(base_dir, base_name + "_temp.html")
            
            with open(temp_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.update_progress(input_path, 60)
            
            # 转换为 PDF
            result = self.html_converter.convert(temp_html_path, output_path, **options)
            self.update_progress(input_path, 100)
            
            result['mode'] = mode
            return result
            
        except json.JSONDecodeError as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to PDF conversion failed: {str(e)}")
        finally:
            if temp_html_path and os.path.exists(temp_html_path):
                try:
                    os.remove(temp_html_path)
                except:
                    pass
