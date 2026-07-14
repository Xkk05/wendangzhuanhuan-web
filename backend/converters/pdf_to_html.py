from pdfminer.high_level import extract_text
from .base import BaseConverter
from typing import Dict, Any
import html
import os

class PdfToHtmlConverter(BaseConverter):
    """PDF 到 HTML 转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加页面渲染模式（将整页渲染为图片）
    2. 添加进度回调
    3. 添加多策略降级
    4. 更好的样式支持
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['html']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 PDF 转换为 HTML（增强版）"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 5)
            
            # 获取总页数（用于页面范围验证）
            import fitz
            with fitz.open(input_path) as doc:
                total_pages = doc.page_count
            
            # 解析页面范围
            raw_page_range = options.get('pdf_page_range') or options.get('page_range')
            pages = self.parse_page_range(raw_page_range, total_pages=total_pages)
            
            # 获取选项
            page_render = options.get('page_render', False)  # 是否使用页面渲染模式
            
            if page_render:
                # 策略1: 页面渲染模式（高质量，保留所有内容）
                result = self._convert_with_page_render(input_path, output_path, pages)
            else:
                # 策略2: 文本提取模式（轻量级）
                result = self._convert_with_text_extraction(input_path, output_path, pages)
            
            self.update_progress(input_path, 100)
            return result
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"PDF to HTML conversion failed: {str(e)}")
    
    def _convert_with_text_extraction(self, input_path: str, output_path: str, pages=None) -> Dict[str, Any]:
        """文本提取模式（原有方案，优化样式）"""
        self.update_progress(input_path, 20)
        
        # 提取文本
        text = extract_text(input_path, page_numbers=pages)
        
        self.update_progress(input_path, 60)
        
        # 构建 HTML（优化样式）
        html_content = [
            '<!DOCTYPE html>',
            '<html lang="zh-CN">',
            '<head>',
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '<title>PDF 转换结果</title>',
            '<style>',
            'body {',
            '  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;',
            '  line-height: 1.6;',
            '  padding: 40px 20px;',
            '  max-width: 900px;',
            '  margin: 0 auto;',
            '  background-color: #f5f5f5;',
            '}',
            '.content {',
            '  background: white;',
            '  padding: 40px;',
            '  border-radius: 8px;',
            '  box-shadow: 0 2px 8px rgba(0,0,0,0.1);',
            '  white-space: pre-wrap;',
            '  word-wrap: break-word;',
            '}',
            '</style>',
            '</head>',
            '<body>',
            '<div class="content">',
            html.escape(text),
            '</div>',
            '</body>',
            '</html>'
        ]
        
        self.update_progress(input_path, 80)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_content))
        
        return {
            'success': True,
            'output_path': output_path,
            'size': self.get_output_size(output_path),
            'method': 'text_extraction'
        }
    
    def _convert_with_page_render(self, input_path: str, output_path: str, pages=None) -> Dict[str, Any]:
        """页面渲染模式（将整页渲染为图片）"""
        try:
            import fitz
        except ImportError:
            raise Exception("PyMuPDF not installed, page render mode unavailable")
        
        self.update_progress(input_path, 15)
        
        doc = fitz.open(input_path)
        total_pages = len(doc)
        
        if total_pages == 0:
            doc.close()
            raise Exception("PDF file is empty")
        
        # 确定要处理的页面
        if pages is None:
            pages_to_process = range(total_pages)
        else:
            pages_to_process = pages
            
        # 创建图片目录
        output_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(output_path))[0]
        images_dir = os.path.join(output_dir, f"{base_name}_images")
        os.makedirs(images_dir, exist_ok=True)
        
        self.update_progress(input_path, 20)
        
        # HTML 头部
        html_content = [
            '<!DOCTYPE html>',
            '<html lang="zh-CN">',
            '<head>',
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '<title>PDF 转换结果</title>',
            '<style>',
            'body {',
            '  font-family: Arial, sans-serif;',
            '  margin: 0;',
            '  padding: 20px;',
            '  background-color: #f5f5f5;',
            '  text-align: center;',
            '}',
            'h1 { color: #333; margin-bottom: 30px; }',
            '.page {',
            '  background: white;',
            '  margin: 20px auto;',
            '  padding: 10px;',
            '  box-shadow: 0 2px 8px rgba(0,0,0,0.1);',
            '  display: inline-block;',
            '  border-radius: 4px;',
            '}',
            '.page-header {',
            '  font-size: 14px;',
            '  color: #666;',
            '  margin-bottom: 10px;',
            '}',
            '.page-image {',
            '  max-width: 100%;',
            '  height: auto;',
            '  display: block;',
            '  border: 1px solid #ddd;',
            '}',
            '</style>',
            '</head>',
            '<body>',
            '<h1>PDF 文档</h1>'
        ]
        
        # 渲染每一页
        processed_count = 0
        total_to_process = len(pages_to_process)
        
        for page_num in pages_to_process:
            if page_num < 0 or page_num >= total_pages:
                continue
                
            page = doc[page_num]
            
            # 高质量渲染
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            
            # 保存图片
            img_filename = f"page_{page_num + 1}.png"
            img_path = os.path.join(images_dir, img_filename)
            pix.save(img_path)
            
            # 相对路径
            img_rel_path = f"{os.path.basename(images_dir)}/{img_filename}"
            
            # 添加到 HTML
            html_content.append(f'''
<div class="page">
  <div class="page-header">第 {page_num + 1} 页 / 共 {total_pages} 页</div>
  <img class="page-image" src="{img_rel_path}" alt="第 {page_num + 1} 页">
</div>''')
            
            pix = None
            processed_count += 1
            
            # 更新进度 (20% ~ 85%)
            progress = 20 + int((processed_count / total_to_process) * 65)
            self.update_progress(input_path, progress)
        
        doc.close()
        
        html_content.append('</body>')
        html_content.append('</html>')
        
        self.update_progress(input_path, 90)
        
        # 保存 HTML
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_content))
        
        return {
            'success': True,
            'output_path': output_path,
            'size': self.get_output_size(output_path),
            'method': 'page_render',
            'total_pages': total_pages
        }
