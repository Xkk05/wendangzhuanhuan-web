from fpdf import FPDF
import os
from .base import BaseConverter
from .html_to_pdf import HtmlToPdfConverter
from typing import Dict, Any

class TxtToPdfConverter(BaseConverter):
    """TXT 到 PDF 转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加进度回调
    2. 支持中文（通过 HTML 中转）
    3. 可配置字体和样式
    4. 更好的换行处理
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['pdf']
        self.html_converter = HtmlToPdfConverter()
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 TXT 转换为 PDF（支持中文）"""
        temp_html_path = None
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 获取选项
            font_size = options.get('font_size', 12)
            line_height = options.get('line_height', 1.6)
            
            # 处理页面设置
            orientation_opt = options.get('orientation')
            orientation = str(orientation_opt).strip() if orientation_opt else '纵向'
            
            page_size_opt = options.get('page_size')
            page_size = str(page_size_opt).strip() if page_size_opt and str(page_size_opt) != 'None' else 'A4'
            
            # Debug log
            try:
                with open('conversion_debug.log', 'a', encoding='utf-8') as f:
                    f.write(f"TXT Conversion: orientation='{orientation}', page_size='{page_size}'\n")
            except:
                pass

            css_orientation = 'landscape' if orientation == '横向' else 'portrait'
            
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            self.update_progress(input_path, 30)
            
            # 转义 HTML 特殊字符
            import html
            text_escaped = html.escape(text)
            
            # 保留换行和空格
            text_html = text_escaped.replace('\n', '<br>').replace(' ', '&nbsp;')
            
            html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Text Document</title>
    <style>
        @page {{
            size: {page_size} {css_orientation} !important;
            margin: 20mm !important;
        }}
        body {{
            font-family: "Microsoft YaHei", "SimSun", "Consolas", monospace;
            background-color: #ffffff;
            color: #333;
            padding: 20px;
            font-size: {font_size}px;
            line-height: {line_height};
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
    </style>
</head>
<body>
{text_html}
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
            
            result['method'] = 'html_conversion'
            return result
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"TXT to PDF conversion failed: {str(e)}")
        finally:
            if temp_html_path and os.path.exists(temp_html_path):
                try:
                    os.remove(temp_html_path)
                except:
                    pass
