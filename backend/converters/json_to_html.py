import json
from .base import BaseConverter
from typing import Dict, Any

class JsonToHtmlConverter(BaseConverter):
    """JSON 到 HTML 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['html']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为 HTML 表格或树状视图"""
        try:
            self.validate_input(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 简单的格式化输出，使用 <pre> 标签保留格式
            # 实际生产中可以使用 json2html 库，但为了减少依赖，这里用简单的 pretty print
            json_str = json.dumps(data, indent=4, ensure_ascii=False)
            
            html_content = [
                '<!DOCTYPE html>',
                '<html>',
                '<head>',
                '<meta charset="utf-8">',
                '<title>JSON View</title>',
                '<style>',
                'body { font-family: Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace; padding: 20px; background-color: #f5f5f5; }',
                'pre { background-color: white; padding: 20px; border-radius: 5px; border: 1px solid #ddd; overflow: auto; }',
                '</style>',
                '</head>',
                '<body>',
                '<h2>JSON Content</h2>',
                f'<pre>{json_str}</pre>',
                '</body>',
                '</html>'
            ]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(html_content))
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to HTML conversion failed: {str(e)}")
