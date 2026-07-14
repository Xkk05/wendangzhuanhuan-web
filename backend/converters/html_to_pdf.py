from bs4 import BeautifulSoup, Comment
from .base import BaseConverter
from typing import Dict, Any
import os
import logging
import subprocess
import platform
import shutil
from pathlib import Path
# html2image and PIL imports removed as they are no longer used for browser print method
# kept reportlab for code mode
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HtmlToPdfConverter(BaseConverter):
    """HTML 到 PDF 转换器（基于浏览器打印模式 - 参考 conversion_core）"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['pdf']
        
    def _get_browser_path(self):
        """获取浏览器路径 (Chrome/Edge)"""
        browser_paths = []

        if platform.system() == 'Windows':
            browser_paths.extend([
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            ])

        for command_name in [
            'google-chrome',
            'google-chrome-stable',
            'chromium',
            'chromium-browser',
            'chrome',
            'msedge',
            'microsoft-edge',
            'microsoft-edge-stable'
        ]:
            resolved = shutil.which(command_name)
            if resolved:
                browser_paths.append(resolved)
        
        for path in browser_paths:
            if os.path.exists(path):
                return path
        return None

    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """
        Convert HTML to PDF using browser's built-in PDF printing.
        This produces high-quality vector PDFs with selectable text.
        """
        try:
            self.validate_input(input_path)
            input_path = os.path.abspath(input_path)
            output_path = os.path.abspath(output_path)
            
            # Check if code mode is enabled
            if options.get('code_mode', False):
                return self._convert_as_code(input_path, output_path, options)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            self.update_progress(input_path, 10)
            
            browser_path = self._get_browser_path()
            if not browser_path:
                raise Exception("No supported browser (Chrome/Edge) found.")
                
            logger.info(f"Using browser: {browser_path}")
            input_uri = Path(input_path).resolve().as_uri()
            
            # Construct command
            # --headless: Run without UI
            # --disable-gpu: Disable GPU acceleration (stable)
            # --print-to-pdf: Output directly to PDF
            # --no-pdf-header-footer: Clean output
            cmd = [
                browser_path,
                '--headless',
                '--disable-gpu',
                '--print-to-pdf=' + output_path,
                '--no-pdf-header-footer',
                '--allow-file-access-from-files',
                input_uri
            ]

            if platform.system() != 'Windows':
                cmd.insert(1, '--no-sandbox')
                cmd.insert(2, '--disable-dev-shm-usage')
            
            # Windows specific startup info to hide console window
            startupinfo = None
            if platform.system() == 'Windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Debug log
            try:
                with open('conversion_debug.log', 'a', encoding='utf-8') as f:
                    f.write(f"Browser Command: {' '.join(cmd)}\n")
            except:
                pass

            self.update_progress(input_path, 30)
            
            # Execute
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            
            if result.returncode != 0:
                logger.error(f"Browser conversion failed: {result.stderr}")
                # Fallback or detailed error check could go here
            
            if not os.path.exists(output_path):
                 # Check if browser outputted to a default location? Unlikely with --print-to-pdf=PATH
                 raise Exception(f"Browser executed but output file was not created. Stderr: {result.stderr}")

            self.update_progress(input_path, 100)
            
            # Get file size
            size = os.path.getsize(output_path)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': size,
                'method': 'browser_print'
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            logger.error(f"HTML to PDF conversion failed: {e}")
            raise Exception(f"HTML to PDF conversion failed: {str(e)}")

    def _apply_page_range(self, output_path: str, page_range: str) -> None:
        try:
            import fitz
        except ImportError as e:
            raise Exception(f"PyMuPDF not installed: {e}")

        if not page_range:
            return

        doc = fitz.open(output_path)
        total_pages = len(doc)

        pages = []
        parts = [p.strip() for p in page_range.split(',') if p.strip()]
        for part in parts:
            if '-' in part:
                segment = part.split('-', 1)
                try:
                    start = int(segment[0])
                    end = int(segment[1])
                except Exception:
                    continue
                if start < 1:
                    start = 1
                if end > total_pages:
                    end = total_pages
                if start <= end:
                    pages.extend(range(start - 1, end))
            else:
                try:
                    num = int(part)
                except Exception:
                    continue
                if 1 <= num <= total_pages:
                    pages.append(num - 1)

        pages = sorted(set(pages))
        if not pages:
            doc.close()
            return

        new_doc = fitz.open()
        for pno in pages:
            new_doc.insert_pdf(doc, from_page=pno, to_page=pno)

        temp_path = output_path + ".tmp"
        new_doc.save(temp_path)
        new_doc.close()
        doc.close()

        os.replace(temp_path, output_path)

    def _convert_as_code(self, input_path: str, output_path: str, options: dict) -> Dict[str, Any]:
        """将HTML源代码转换为PDF（代码格式）- 使用ReportLab"""
        from reportlab.lib.pagesizes import A4, A3, letter, legal
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.colors import HexColor
        
        self.update_progress(input_path, 20)
        
        # Register a CJK-capable font when available so containerized Linux builds
        # can still render Chinese text.
        font_name = 'Courier'
        for font_path, kwargs in [
            (r"C:\Windows\Fonts\msyh.ttc", {'subfontIndex': 0}),
            (r"C:\Windows\Fonts\simsun.ttc", {'subfontIndex': 0}),
            ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', {'subfontIndex': 0}),
            ('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', {}),
            ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', {}),
        ]:
            try:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path, **kwargs))
                    font_name = 'ChineseFont'
                    break
            except Exception:
                continue
        
        # Read HTML source code
        with open(input_path, 'r', encoding='utf-8') as f:
            html_code = f.read()
        
        self.update_progress(input_path, 40)
        
        # Get page size
        page_size_name = options.get('page_size', 'A4')
        page_sizes = {
            'A4': A4,
            'A3': A3,
            'Letter': letter,
            'Legal': legal
        }
        page_size = page_sizes.get(page_size_name, A4)
        
        # Create PDF
        c = canvas.Canvas(output_path, pagesize=page_size)
        width, height = page_size
        
        # Settings
        margin = 1.5 * cm
        font_size = 8
        line_height = font_size * 1.4
        
        # Calculate usable area
        usable_width = width - 2 * margin
        usable_height = height - 2 * margin
        
        # Split code into lines
        lines = html_code.split('\n')
        
        self.update_progress(input_path, 60)
        
        # Draw code
        y = height - margin
        line_num = 1
        
        for line in lines:
            # Check if need new page
            if y < margin + line_height:
                c.showPage()
                y = height - margin
            
            # Draw line number
            c.setFont(font_name, font_size)
            c.setFillColor(HexColor('#666666'))
            c.drawRightString(margin + 30, y, str(line_num))
            
            # Draw separator
            c.setStrokeColor(HexColor('#cccccc'))
            c.line(margin + 35, y - 2, margin + 35, y + font_size)
            
            # Draw code line
            c.setFillColor(HexColor('#000000'))
            
            # Handle long lines - wrap text
            x_pos = margin + 40
            remaining_line = line
            max_chars = int((usable_width - 45) / (font_size * 0.6))  # Approximate chars per line
            
            while remaining_line:
                if len(remaining_line) <= max_chars:
                    c.drawString(x_pos, y, remaining_line)
                    break
                else:
                    # Find good break point
                    chunk = remaining_line[:max_chars]
                    c.drawString(x_pos, y, chunk)
                    remaining_line = remaining_line[max_chars:]
                    
                    # Move to next line
                    y -= line_height
                    if y < margin + line_height:
                        c.showPage()
                        y = height - margin
                    
                    # Continue with indentation
                    x_pos = margin + 50
            
            y -= line_height
            line_num += 1
        
        self.update_progress(input_path, 80)
        
        c.save()
        
        self.update_progress(input_path, 100)
        
        return {
            'success': True,
            'output_path': output_path,
            'size': self.get_output_size(output_path),
            'method': 'code_mode_reportlab'
        }
