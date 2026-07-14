from .base import BaseConverter
from typing import Dict, Any
import html

class XmlToHtmlConverter(BaseConverter):
    """XML 到 HTML 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['html']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 XML 转换为 HTML 视图"""
        try:
            self.validate_input(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # 转义 XML 内容以在 HTML 中显示
            escaped_xml = html.escape(xml_content)
            
            html_content = [
                '<!DOCTYPE html>',
                '<html>',
                '<head>',
                '<meta charset="utf-8">',
                '<title>XML View</title>',
                '<style>',
                'body { font-family: Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace; padding: 20px; background-color: #f5f5f5; }',
                'pre { background-color: white; padding: 20px; border-radius: 5px; border: 1px solid #ddd; overflow: auto; color: #000; }',
                '</style>',
                '</head>',
                '<body>',
                '<h2>XML Content</h2>',
                f'<pre>{escaped_xml}</pre>',
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
            raise Exception(f"XML to HTML conversion failed: {str(e)}")
