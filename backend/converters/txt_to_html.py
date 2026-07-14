import html
from .base import BaseConverter
from typing import Dict, Any

class TxtToHtmlConverter(BaseConverter):
    """TXT 到 HTML 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['html']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 TXT 转换为 HTML"""
        try:
            self.validate_input(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 构建简单的 HTML
            html_content = [
                '<!DOCTYPE html>',
                '<html>',
                '<head>',
                '<meta charset="utf-8">',
                '<style>',
                'body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }',
                'p { margin-bottom: 1em; }',
                '</style>',
                '</head>',
                '<body>'
            ]
            
            for line in lines:
                line = line.strip()
                if line:
                    # 转义 HTML 特殊字符
                    escaped_line = html.escape(line)
                    html_content.append(f'<p>{escaped_line}</p>')
            
            html_content.append('</body>')
            html_content.append('</html>')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(html_content))
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"TXT to HTML conversion failed: {str(e)}")
