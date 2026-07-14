import os
import subprocess
import shutil
import html
import logging
from docx import Document
from .base import BaseConverter
from .html_to_pdf import HtmlToPdfConverter
from typing import Dict, Any
from backend.utils.logger import setup_logger

class DocxToPdfConverter(BaseConverter):
    """DOCX 到 PDF 转换器（优化版 - 参考 conversion_core）"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['pdf']
        self.html_converter = HtmlToPdfConverter()
        self.soffice_path = self._find_libreoffice()
        self.logger = setup_logger('DocxToPdf')
    
    def _find_libreoffice(self) -> str:
        """查找 LibreOffice 路径"""
        # 1. 优先尝试集成路径 (resources/libreoffice)
        from conversion_core.tools.office_to_pdf import get_bundled_libreoffice_path
        bundled_path = get_bundled_libreoffice_path()
        if bundled_path and os.path.exists(bundled_path):
            return bundled_path

        # 2. 尝试系统默认路径
        paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        
        # 3. 检查环境变量 PATH
        return shutil.which("soffice") or shutil.which("libreoffice")
    
    def _has_word(self) -> bool:
        """检查是否有 Microsoft Word"""
        try:
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.Quit()
            return True
        except:
            return False
    
    def _convert_with_word(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """使用 Microsoft Word 转换 (优化版)"""
        import win32com.client
        import pythoncom
        
        # 初始化 COM
        pythoncom.CoInitialize()
        
        word = None
        doc = None
        
        try:
            # 转换为绝对路径
            input_path = os.path.abspath(input_path)
            output_path = os.path.abspath(output_path)
            
            self.logger.info(f"使用 Word 转换: {input_path} -> {output_path}")
            
            # 启动 Word
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0  # 不显示警告
            
            # 打开文档
            doc = word.Documents.Open(input_path, ReadOnly=True)
            
            # 保存为 PDF
            # wdFormatPDF = 17
            doc.SaveAs(output_path, FileFormat=17)
            
            return {'method': 'microsoft_word'}
            
        except Exception as e:
            self.logger.error(f"Word 转换失败: {str(e)}")
            raise e
        finally:
            # 清理资源
            try:
                if doc:
                    doc.Close(SaveChanges=False)
            except:
                pass
            
            try:
                if word:
                    word.Quit()
            except:
                pass
            
            # 清理 COM
            try:
                pythoncom.CoUninitialize()
            except:
                pass
    
    def _convert_with_libreoffice(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """使用 LibreOffice 转换"""
        output_dir = os.path.dirname(output_path) or os.getcwd()
        cmd = [self.soffice_path, '--headless', '--convert-to', 'pdf', '--outdir', output_dir, input_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise Exception(f"LibreOffice 转换失败: {result.stderr}")
        
        # 重命名输出文件
        input_basename = os.path.splitext(os.path.basename(input_path))[0]
        generated_pdf = os.path.join(output_dir, input_basename + '.pdf')
        if generated_pdf != output_path and os.path.exists(generated_pdf):
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(generated_pdf, output_path)
        
        return {'method': 'libreoffice'}
    
    def _convert_with_html(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """使用 HTML 中转方式转换（兜底方案 - 增强版，支持图片）"""
        import base64
        from docx.oxml.text.paragraph import CT_P
        from docx.oxml.table import CT_Tbl
        from docx.table import _Cell, Table
        from docx.text.paragraph import Paragraph
        
        doc = Document(input_path)
        base_dir = os.path.dirname(output_path) or os.getcwd()
        base_name = os.path.splitext(os.path.basename(output_path))[0]
        
        lines = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '<meta charset="utf-8">',
            '<style>',
            'html, body { background-color: #ffffff; color: #000000; margin: 40px; font-family: "Microsoft YaHei", "SimSun", sans-serif; font-size: 14px; }',
            'p { margin: 0.8em 0; line-height: 1.8; }',
            'img { max-width: 100%; height: auto; margin: 1em 0; display: block; }',
            'table { border-collapse: collapse; width: 100%; margin: 1em 0; }',
            'td, th { border: 1px solid #ddd; padding: 8px; text-align: left; }',
            'th { background-color: #f2f2f2; font-weight: bold; }',
            'h1 { font-size: 24px; font-weight: bold; margin: 1em 0 0.5em 0; }',
            'h2 { font-size: 20px; font-weight: bold; margin: 1em 0 0.5em 0; }',
            'h3 { font-size: 18px; font-weight: bold; margin: 1em 0 0.5em 0; }',
            'strong, b { font-weight: bold; }',
            'em, i { font-style: italic; }',
            'ul, ol { margin: 0.5em 0; padding-left: 2em; }',
            'li { margin: 0.3em 0; }',
            '</style>',
            '</head>',
            '<body>',
        ]
        
        # 提取所有图片关系
        image_counter = 0
        
        # 遍历文档的所有元素（段落和表格）
        for element in doc.element.body:
            if isinstance(element, CT_P):
                para = Paragraph(element, doc)
                
                # 检查段落中是否有图片
                has_image = False
                for run in para.runs:
                    # 检查 run 中的图片
                    for drawing in run.element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing'):
                        has_image = True
                        # 提取图片
                        for blip in drawing.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
                            embed = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                            if embed:
                                try:
                                    image_part = doc.part.related_parts[embed]
                                    image_bytes = image_part.blob
                                    # 转换为 base64
                                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                                    # 获取图片类型
                                    content_type = image_part.content_type
                                    lines.append(f'<img src="data:{content_type};base64,{image_base64}" alt="Image {image_counter}" />')
                                    image_counter += 1
                                except Exception as e:
                                    print(f"[DocxToPdf] 提取图片失败: {e}")
                
                # 如果没有图片，处理文本
                if not has_image:
                    text = html.escape(para.text or '')
                    if not text.strip():
                        continue
                    
                    # 检测标题样式
                    style_name = para.style.name.lower() if para.style else ''
                    if 'heading 1' in style_name or 'title' in style_name:
                        lines.append(f"<h1>{text}</h1>")
                    elif 'heading 2' in style_name:
                        lines.append(f"<h2>{text}</h2>")
                    elif 'heading 3' in style_name:
                        lines.append(f"<h3>{text}</h3>")
                    else:
                        # 检测文本格式
                        formatted_text = text
                        if para.runs:
                            formatted_parts = []
                            for run in para.runs:
                                run_text = html.escape(run.text or '')
                                if run.bold:
                                    run_text = f"<strong>{run_text}</strong>"
                                if run.italic:
                                    run_text = f"<em>{run_text}</em>"
                                formatted_parts.append(run_text)
                            formatted_text = ''.join(formatted_parts)
                        lines.append(f"<p>{formatted_text}</p>")
            
            elif isinstance(element, CT_Tbl):
                table = Table(element, doc)
                lines.append('<table>')
                for i, row in enumerate(table.rows):
                    lines.append('<tr>')
                    for cell in row.cells:
                        cell_text = html.escape(cell.text or '')
                        tag = 'th' if i == 0 else 'td'
                        lines.append(f"<{tag}>{cell_text}</{tag}>")
                    lines.append('</tr>')
                lines.append('</table>')
        
        lines.append('</body></html>')
        
        temp_html_path = os.path.join(base_dir, base_name + "_temp.html")
        
        try:
            with open(temp_html_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            self.html_converter.convert(temp_html_path, output_path, **options)
        finally:
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)
        
        return {'method': 'html_fallback', 'images_extracted': image_counter}

    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 DOCX 转换为 PDF（多策略降级）"""
        try:
            self.validate_input(input_path)
            
            # 检查文件头，防止非 DOCX 文件被错误处理（例如伪装成 docx 的 PDF）
            try:
                with open(input_path, 'rb') as f:
                    header = f.read(5)
                    # PDF magic number: %PDF- (0x25 0x50 0x44 0x46 0x2D)
                    if header.startswith(b'%PDF'):
                        raise ValueError("输入文件似乎是 PDF 文件，而不是 Word 文档。请使用 PDF 转 Word 功能，或修改文件扩展名。")
            except Exception as e:
                if isinstance(e, ValueError):
                    raise e
                # 忽略文件读取错误，继续尝试转换
                pass

            self.update_progress(input_path, 5)
            
            print(f"[DocxToPdf] 开始转换: {input_path} -> {output_path}")
            
            result = {}
            errors = []

            has_page_options = any(
                key in options and options.get(key)
                for key in ['page_size', 'orientation', 'page_range', 'watermark_text']
            )

            if has_page_options:
                self.logger.info("[DocxToPdf] Detected page/watermark options, using HTML fallback")
                self.update_progress(input_path, 60)
                result = self._convert_with_html(input_path, output_path, **options)
                self.update_progress(input_path, 100)
                self.logger.info("[DocxToPdf] [OK] HTML fallback conversion successful (with page/watermark settings)")
                result['method'] = 'html_fallback'
                return {
                    'success': True,
                    'output_path': output_path,
                    'size': self.get_output_size(output_path),
                    **result
                }
            
            if self._has_word():
                try:
                    self.logger.info("[DocxToPdf] Trying Microsoft Word conversion...")
                    self.update_progress(input_path, 10)
                    result = self._convert_with_word(input_path, output_path)
                    self.update_progress(input_path, 100)
                    
                    self.logger.info("[DocxToPdf] [OK] Word conversion successful")
                    return {
                        'success': True,
                        'output_path': output_path,
                        'size': self.get_output_size(output_path),
                        **result
                    }
                except Exception as e1:
                    errors.append(f"Word: {str(e1)}")
                    self.logger.warning(f"[DocxToPdf] [FAIL] Word conversion failed: {e1}")
                    import traceback
                    self.logger.warning(traceback.format_exc())
                    self.update_progress(input_path, 20)
            else:
                self.logger.info("[DocxToPdf] Microsoft Word not available")
            
            # 策略2: LibreOffice（开源方案）
            if self.soffice_path:
                try:
                    self.logger.info("[DocxToPdf] Trying LibreOffice conversion...")
                    self.update_progress(input_path, 30)
                    result = self._convert_with_libreoffice(input_path, output_path)
                    self.update_progress(input_path, 100)
                    
                    self.logger.info("[DocxToPdf] [OK] LibreOffice conversion successful")
                    return {
                        'success': True,
                        'output_path': output_path,
                        'size': self.get_output_size(output_path),
                        **result
                    }
                except Exception as e2:
                    errors.append(f"LibreOffice: {str(e2)}")
                    self.logger.warning(f"[DocxToPdf] [FAIL] LibreOffice conversion failed: {e2}")
                    import traceback
                    self.logger.warning(traceback.format_exc())
                    self.update_progress(input_path, 50)
            else:
                self.logger.info("[DocxToPdf] LibreOffice not available")
            
            # 策略3: HTML 中转（兜底方案，基础文本提取）
            try:
                self.logger.info("[DocxToPdf] Trying HTML fallback...")
                self.update_progress(input_path, 60)
                result = self._convert_with_html(input_path, output_path, **options)
                self.update_progress(input_path, 100)
                
                self.logger.info("[DocxToPdf] [OK] HTML fallback conversion successful (may lose some formatting)")
                result['warning'] = 'Used HTML fallback (basic text extraction only)'
                return {
                    'success': True,
                    'output_path': output_path,
                    'size': self.get_output_size(output_path),
                    **result
                }
            except Exception as e3:
                errors.append(f"HTML: {str(e3)}")
                self.logger.error(f"[DocxToPdf] [FAIL] HTML fallback failed: {e3}")
                import traceback
                self.logger.error(traceback.format_exc())
            
            # 所有策略都失败
            error_msg = "All conversion methods failed: " + "; ".join(errors)
            self.logger.error("[DocxToPdf] [FAIL] All conversion methods failed")
            raise Exception(error_msg)
            
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            self.cleanup_on_error(output_path)
            raise Exception(f"DOCX to PDF conversion failed: {str(e)}")
