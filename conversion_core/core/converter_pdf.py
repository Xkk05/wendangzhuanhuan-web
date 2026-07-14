#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF转换器 - 专门处理文件转PDF功能
"""

import os
import platform
import subprocess
import shutil
import csv
import json
from pathlib import Path
from conversion_core.core.base import Converter
from conversion_core.tools.office_to_pdf import OfficeToPDF


class PDFConverter(Converter):
    """PDF转换器"""
    
    def convert(self, file_path):
        """转换文件为PDF"""
        try:
            ext = Path(file_path).suffix.lower()
            
            if ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
                return self._convert_office_to_pdf(file_path)
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']:
                return self._convert_image_to_pdf(file_path)
            elif ext == '.txt':
                return self._convert_text_to_pdf(file_path)
            elif ext == '.md':
                return self._convert_markdown_to_pdf(file_path)
            elif ext in ['.html', '.htm']:
                return self._convert_html_to_pdf(file_path)
            elif ext == '.csv':
                return self._convert_csv_to_pdf(file_path)
            elif ext in ['.py', '.js', '.java', '.c', '.cpp']:
                return self._convert_code_to_pdf(file_path)
            else:
                return {'success': False, 'error': f'不支持的文件格式: {ext}'}
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': f'转换失败: {str(e)}'}
    
    def _convert_office_to_pdf(self, file_path):
        """Office文件转PDF"""
        # 检查文件是否存在且不为空
        if not os.path.exists(file_path):
            return {'success': False, 'error': '文件不存在'}
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return {'success': False, 'error': '文件为空，无法转换'}
        
        # 推送开始进度
        self.update_progress(file_path, 10)
        
        try:
            output_file = self.get_output_filename(file_path, 'pdf')
            
            self.update_progress(file_path, 30)
            
            # 使用OfficeToPDF转换
            result = OfficeToPDF.convert(file_path, output_file)
            
            self.update_progress(file_path, 90)
            
            if result['success']:
                self.update_progress(file_path, 100)
                return {'success': True, 'output_file': result['output_file']}
            else:
                return {'success': False, 'error': result['error']}
        
        except Exception as e:
            return {'success': False, 'error': f'Office转PDF失败: {str(e)}'}
    
    def _convert_image_to_pdf(self, file_path):
        """图片转PDF - 使用多种方法尝试"""
        # 检查文件是否存在且不为空
        if not os.path.exists(file_path):
            return {'success': False, 'error': '文件不存在'}
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return {'success': False, 'error': '文件为空，无法转换'}
        
        # 推送开始进度
        self.update_progress(file_path, 10)
        
        # 方法1: 尝试使用PIL直接保存为PDF（最简单可靠）
        try:
            return self._convert_image_to_pdf_with_pil(file_path)
        except Exception as e1:
            print(f"[图片转PDF] PIL方法失败: {e1}")
        
        # 方法2: 尝试使用reportlab
        try:
            return self._convert_image_to_pdf_with_reportlab(file_path)
        except Exception as e2:
            print(f"[图片转PDF] reportlab方法失败: {e2}")
        
        # 方法3: 尝试使用PyMuPDF
        try:
            return self._convert_image_to_pdf_with_pymupdf(file_path)
        except Exception as e3:
            print(f"[图片转PDF] PyMuPDF方法失败: {e3}")
        
        return {'success': False, 'error': f'图片转PDF失败，所有方法都不可用。请确保安装了Pillow库。'}
    
    def _convert_image_to_pdf_with_pil(self, file_path):
        """使用PIL直接将图片保存为PDF"""
        from PIL import Image
        
        self.update_progress(file_path, 30)
        
        # 打开图片
        img = Image.open(file_path)
        
        # 如果是RGBA模式，转换为RGB（PDF不支持透明通道）
        if img.mode == 'RGBA':
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # 使用alpha通道作为mask
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        self.update_progress(file_path, 60)
        
        # 创建输出文件路径
        output_file = self.get_output_filename(file_path, 'pdf')
        
        # 直接保存为PDF
        img.save(output_file, 'PDF', resolution=100.0)
        
        self.update_progress(file_path, 100)
        return {'success': True, 'output_file': output_file}
    
    def _convert_image_to_pdf_with_reportlab(self, file_path):
        """使用reportlab将图片转换为PDF"""
        from PIL import Image
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        self.update_progress(file_path, 30)
        
        # 打开图片
        img = Image.open(file_path)
        
        # 创建PDF
        output_file = self.get_output_filename(file_path, 'pdf')
        c = canvas.Canvas(output_file, pagesize=A4)
        
        # 获取A4页面尺寸
        page_width, page_height = A4
        
        # 计算图片尺寸，保持宽高比
        img_width, img_height = img.size
        aspect_ratio = img_height / img_width
        
        # 设置边距
        margin = 50
        max_width = page_width - 2 * margin
        max_height = page_height - 2 * margin
        
        # 计算最终尺寸
        if img_width > img_height:
            final_width = min(max_width, img_width)
            final_height = final_width * aspect_ratio
            if final_height > max_height:
                final_height = max_height
                final_width = final_height / aspect_ratio
        else:
            final_height = min(max_height, img_height)
            final_width = final_height / aspect_ratio
            if final_width > max_width:
                final_width = max_width
                final_height = final_width * aspect_ratio
        
        # 居中放置
        x = (page_width - final_width) / 2
        y = (page_height - final_height) / 2
        
        self.update_progress(file_path, 60)
        
        # 添加图片到PDF
        c.drawImage(file_path, x, y, width=final_width, height=final_height)
        
        self.update_progress(file_path, 90)
        
        # 保存PDF
        c.save()
        
        self.update_progress(file_path, 100)
        return {'success': True, 'output_file': output_file}
    
    def _convert_image_to_pdf_with_pymupdf(self, file_path):
        """使用PyMuPDF将图片转换为PDF"""
        import fitz  # PyMuPDF
        
        self.update_progress(file_path, 30)
        
        # 创建新的PDF文档
        doc = fitz.open()
        
        # 打开图片
        img = fitz.open(file_path)
        
        # 将图片转换为PDF页面
        pdfbytes = img.convert_to_pdf()
        img.close()
        
        self.update_progress(file_path, 60)
        
        # 打开转换后的PDF
        imgpdf = fitz.open("pdf", pdfbytes)
        
        # 插入页面
        doc.insert_pdf(imgpdf)
        imgpdf.close()
        
        self.update_progress(file_path, 90)
        
        # 保存PDF
        output_file = self.get_output_filename(file_path, 'pdf')
        doc.save(output_file)
        doc.close()
        
        self.update_progress(file_path, 100)
        return {'success': True, 'output_file': output_file}
    
    def _convert_text_to_pdf(self, file_path):
        """文本转PDF"""
        # 检查文件是否存在且不为空
        if not os.path.exists(file_path):
            return {'success': False, 'error': '文件不存在'}
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return {'success': False, 'error': '文件为空，无法转换'}
        
        # 推送开始进度
        self.update_progress(file_path, 10)
        
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import platform
        except ImportError as e:
            return {'success': False, 'error': f'reportlab库导入失败: {str(e)}'}
        
        try:
            # 读取文本文件
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            self.update_progress(file_path, 30)
            
            # 创建PDF
            output_file = self.get_output_filename(file_path, 'pdf')
            c = canvas.Canvas(output_file, pagesize=A4)
            
            # 注册中文字体
            try:
                if platform.system() == 'Windows':
                    # Windows系统使用系统字体
                    font_paths = [
                        'C:/Windows/Fonts/simsun.ttc',
                        'C:/Windows/Fonts/simhei.ttf',
                        'C:/Windows/Fonts/msyh.ttc'
                    ]
                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            pdfmetrics.registerFont(TTFont('Chinese', font_path))
                            break
                    else:
                        # 如果没有找到中文字体，使用默认字体
                        c.setFont("Helvetica", 12)
                        font_name = "Helvetica"
                else:
                    # 非Windows系统使用默认字体
                    c.setFont("Helvetica", 12)
                    font_name = "Helvetica"
                
                if 'Chinese' in locals():
                    c.setFont("Chinese", 12)
                    font_name = "Chinese"
                else:
                    font_name = "Helvetica"
            except:
                c.setFont("Helvetica", 12)
                font_name = "Helvetica"
            
            # 页面设置
            page_width, page_height = A4
            margin = 50
            line_height = 16
            max_lines_per_page = int((page_height - 2 * margin) / line_height)
            
            self.update_progress(file_path, 50)
            
            # 分页处理文本
            lines = text_content.split('\n')
            current_line = 0
            
            while current_line < len(lines):
                # 新页面
                y_position = page_height - margin
                lines_on_page = 0
                
                while current_line < len(lines) and lines_on_page < max_lines_per_page:
                    line = lines[current_line]
                    
                    # 处理长行（自动换行）
                    if len(line) > 80:  # 假设每行最多80个字符
                        # 简单的换行处理
                        while len(line) > 80:
                            c.drawString(margin, y_position, line[:80])
                            line = line[80:]
                            y_position -= line_height
                            lines_on_page += 1
                            if lines_on_page >= max_lines_per_page:
                                break
                    
                    if lines_on_page < max_lines_per_page:
                        c.drawString(margin, y_position, line)
                        y_position -= line_height
                        lines_on_page += 1
                    
                    current_line += 1
                
                # 如果还有内容，创建新页面
                if current_line < len(lines):
                    c.showPage()
                    if font_name == "Chinese":
                        c.setFont("Chinese", 12)
                    else:
                        c.setFont("Helvetica", 12)
            
            self.update_progress(file_path, 90)
            
            # 保存PDF
            c.save()
            
            self.update_progress(file_path, 100)
            return {'success': True, 'output_file': output_file}
        
        except Exception as e:
            return {'success': False, 'error': f'文本转PDF失败: {str(e)}'}

    # ================= HTML / Markdown / Code / CSV 转换增强 =================

    def _get_browser_path(self):
        """获取浏览器路径 (Chrome/Edge)"""
        if platform.system() != 'Windows':
            return None
            
        # 常见浏览器路径
        browser_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        ]
        
        for path in browser_paths:
            if os.path.exists(path):
                return path
        return None

    def _convert_html_to_pdf(self, file_path):
        """HTML转PDF (支持UI/CSS)"""
        self.update_progress(file_path, 10)
        output_file = self.get_output_filename(file_path, 'pdf')
        
        # 策略1: 使用浏览器无头模式打印 (最佳效果，支持现代CSS/JS)
        browser_path = self._get_browser_path()
        if browser_path:
            try:
                print(f"[HTML转PDF] 使用浏览器: {browser_path}")
                cmd = [
                    browser_path,
                    '--headless',
                    '--disable-gpu',
                    '--print-to-pdf=' + output_file,
                    '--no-pdf-header-footer',
                    file_path
                ]
                # Windows下隐藏命令行窗口
                startupinfo = None
                if platform.system() == 'Windows':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
                
                if result.returncode == 0 and os.path.exists(output_file):
                    self.update_progress(file_path, 100)
                    return {'success': True, 'output_file': output_file}
                else:
                    print(f"[HTML转PDF] 浏览器转换失败: {result.stderr}")
            except Exception as e:
                print(f"[HTML转PDF] 浏览器转换异常: {e}")
        
        self.update_progress(file_path, 40)
        
        # 策略2: 使用WeasyPrint (高质量CSS支持)
        try:
            from weasyprint import HTML
            print("[HTML转PDF] 使用WeasyPrint")
            HTML(filename=file_path).write_pdf(output_file)
            self.update_progress(file_path, 100)
            return {'success': True, 'output_file': output_file}
        except ImportError:
            print("[HTML转PDF] WeasyPrint未安装")
        except Exception as e:
            print(f"[HTML转PDF] WeasyPrint转换失败: {e}")

        # 策略3: 使用PdfKit (需要wkhtmltopdf)
        try:
            import pdfkit
            print("[HTML转PDF] 使用PdfKit")
            pdfkit.from_file(file_path, output_file)
            self.update_progress(file_path, 100)
            return {'success': True, 'output_file': output_file}
        except ImportError:
            pass
        except Exception as e:
            print(f"[HTML转PDF] PdfKit转换失败: {e}")
            
        self.update_progress(file_path, 70)
        
        # 策略4: 使用PyMuPDF (降级方案)
        try:
            import fitz
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            doc = fitz.open()
            try:
                story = fitz.Story(html=html_content)
                page_width = 595
                page_height = 842
                margin = 50
                content_rect = fitz.Rect(margin, margin, page_width - margin, page_height - margin)
                more = True
                while more:
                    page = doc.new_page(width=page_width, height=page_height)
                    more, _ = story.place(content_rect)
                    story.draw(page)
                
                doc.save(output_file)
                doc.close()
                self.update_progress(file_path, 100)
                return {'success': True, 'output_file': output_file}
            except AttributeError:
                pass
        except Exception as e:
            print(f"[HTML转PDF] PyMuPDF转换失败: {e}")

        return {'success': False, 'error': 'HTML转PDF失败: 未找到可用的转换引擎 (建议安装Chrome浏览器或weasyprint库)'}

    def _convert_markdown_to_pdf(self, file_path):
        """Markdown转PDF (通过HTML中间格式)"""
        try:
            import markdown
            
            self.update_progress(file_path, 10)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 转换为HTML
            html_body = markdown.markdown(
                md_content,
                extensions=['tables', 'fenced_code', 'codehilite', 'toc', 'nl2br', 'sane_lists']
            )
            
            # 添加Github风格样式
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; font-size: 16px; line-height: 1.5; color: #24292e; margin: 40px; }}
                    h1, h2, h3, h4, h5, h6 {{ margin-top: 24px; margin-bottom: 16px; font-weight: 600; line-height: 1.25; }}
                    h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; }}
                    h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; }}
                    p {{ margin-top: 0; margin-bottom: 16px; }}
                    code {{ padding: .2em .4em; margin: 0; font-size: 85%; background-color: #f6f8fa; border-radius: 3px; font-family: SFMono-Regular,Consolas,"Liberation Mono",Menlo,monospace; }}
                    pre {{ padding: 16px; overflow: auto; font-size: 85%; line-height: 1.45; background-color: #f6f8fa; border-radius: 3px; }}
                    pre code {{ padding: 0; background-color: transparent; }}
                    blockquote {{ padding: 0 1em; color: #6a737d; border-left: .25em solid #dfe2e5; margin: 0 0 16px 0; }}
                    table {{ display: block; width: 100%; overflow: auto; border-spacing: 0; border-collapse: collapse; margin-bottom: 16px; }}
                    table th, table td {{ padding: 6px 13px; border: 1px solid #dfe2e5; }}
                    table th {{ font-weight: 600; background-color: #f6f8fa; }}
                    table tr {{ background-color: #fff; border-top: 1px solid #c6cbd1; }}
                    table tr:nth-child(2n) {{ background-color: #f6f8fa; }}
                    img {{ max-width: 100%; box-sizing: content-box; background-color: #fff; }}
                </style>
            </head>
            <body>
                {html_body}
            </body>
            </html>
            """
            
            # 保存为临时HTML文件
            temp_html = file_path + ".temp.html"
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.update_progress(file_path, 30)
            
            # 调用HTML转PDF
            try:
                result = self._convert_html_to_pdf(temp_html)
                # 修正输出文件名 (移除.temp.html.pdf -> .pdf)
                if result['success']:
                    real_output = self.get_output_filename(file_path, 'pdf')
                    if result['output_file'] != real_output:
                        if os.path.exists(real_output):
                            os.remove(real_output)
                        os.rename(result['output_file'], real_output)
                        result['output_file'] = real_output
                return result
            finally:
                if os.path.exists(temp_html):
                    os.remove(temp_html)
                    
        except ImportError:
            return {'success': False, 'error': 'Markdown转换依赖缺失，请安装markdown库'}
        except Exception as e:
            return {'success': False, 'error': f'Markdown转PDF失败: {e}'}

    def _convert_csv_to_pdf(self, file_path):
        """CSV转PDF (通过HTML表格)"""
        try:
            self.update_progress(file_path, 10)
            
            # 读取CSV
            rows = []
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f)
                for row in reader:
                    rows.append(row)
            
            if not rows:
                return {'success': False, 'error': 'CSV文件为空'}
            
            # 生成HTML表格
            html_rows = []
            for i, row in enumerate(rows):
                tag = 'th' if i == 0 else 'td'
                cells = [f'<{tag}>{cell}</{tag}>' for cell in row]
                html_rows.append(f'<tr>{"".join(cells)}</tr>')
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; font-weight: bold; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                </style>
            </head>
            <body>
                <h2>{os.path.basename(file_path)}</h2>
                <table>
                    {''.join(html_rows)}
                </table>
            </body>
            </html>
            """
            
            # 保存临时文件并转换
            temp_html = file_path + ".temp.html"
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            try:
                result = self._convert_html_to_pdf(temp_html)
                # 修正文件名
                if result['success']:
                    real_output = self.get_output_filename(file_path, 'pdf')
                    if result['output_file'] != real_output:
                        if os.path.exists(real_output):
                            os.remove(real_output)
                        os.rename(result['output_file'], real_output)
                        result['output_file'] = real_output
                return result
            finally:
                if os.path.exists(temp_html):
                    os.remove(temp_html)
                    
        except Exception as e:
            return {'success': False, 'error': f'CSV转PDF失败: {e}'}

    def _convert_code_to_pdf(self, file_path):
        """代码文件转PDF (语法高亮)"""
        try:
            from pygments import highlight
            from pygments.lexers import get_lexer_for_filename, TextLexer
            from pygments.formatters import HtmlFormatter
            
            self.update_progress(file_path, 10)
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                code_content = f.read()
            
            try:
                lexer = get_lexer_for_filename(file_path)
            except:
                lexer = TextLexer()
            
            formatter = HtmlFormatter(full=True, style='colorful', linenos=True)
            html_content = highlight(code_content, lexer, formatter)
            
            # 注入更好的字体样式
            html_content = html_content.replace('body {', 'body { font-family: Consolas, "Courier New", monospace; ')
            
            # 保存临时文件并转换
            temp_html = file_path + ".temp.html"
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            try:
                result = self._convert_html_to_pdf(temp_html)
                # 修正文件名
                if result['success']:
                    real_output = self.get_output_filename(file_path, 'pdf')
                    if result['output_file'] != real_output:
                        if os.path.exists(real_output):
                            os.remove(real_output)
                        os.rename(result['output_file'], real_output)
                        result['output_file'] = real_output
                return result
            finally:
                if os.path.exists(temp_html):
                    os.remove(temp_html)
                    
        except ImportError:
            return {'success': False, 'error': '代码高亮依赖缺失，请安装Pygments库'}
        except Exception as e:
            return {'success': False, 'error': f'代码转PDF失败: {e}'}
