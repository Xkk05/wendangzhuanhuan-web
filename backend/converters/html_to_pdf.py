from bs4 import BeautifulSoup, Comment
from .base import BaseConverter
from typing import Dict, Any
import os
import logging
import subprocess
import platform
import shutil
import re
from pathlib import Path
# html2image and PIL imports removed as they are no longer used for browser print method
from backend.utils.structured_text import normalize_hex_color
from backend.utils.text_utils import read_text_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HtmlToPdfConverter(BaseConverter):
    """HTML 到 PDF 转换器（基于浏览器打印模式 - 参考 conversion_core）"""

    PRINT_FIT_CSS = """
@media print {
    html, body {
        max-width: 100% !important;
        min-width: 0 !important;
        box-sizing: border-box;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    *, *::before, *::after {
        box-sizing: inherit;
    }
    body * {
        max-width: 100% !important;
        min-width: 0 !important;
    }
    img, svg, canvas, video {
        max-width: 100% !important;
        height: auto !important;
    }
    table {
        width: 100% !important;
        max-width: 100% !important;
        table-layout: fixed !important;
        border-collapse: collapse;
    }
    col, colgroup {
        width: auto !important;
    }
    th, td {
        min-width: 0 !important;
        max-width: 100% !important;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    pre, code {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
}
"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['pdf']

    def _append_style(self, soup: BeautifulSoup, css: str) -> None:
        style = soup.new_tag('style')
        style.string = css
        (soup.head or soup).append(style)
        
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

    def _prepare_html_content(self, html_content: str, options: dict) -> str:
        soup = BeautifulSoup(html_content, 'html.parser')

        css_handling = str(options.get('css_handling') or '').strip().lower()
        remove_css = 'remove' in css_handling or '移除' in css_handling
        if remove_css:
            for tag in soup.find_all('style'):
                tag.decompose()
            for tag in soup.find_all('link'):
                rel = tag.get('rel') or []
                if any(str(item).lower() == 'stylesheet' for item in rel):
                    tag.decompose()
            for tag in soup.find_all(style=True):
                del tag['style']

        if options.get('remove_scripts'):
            for tag in soup.find_all('script'):
                tag.decompose()

        if options.get('remove_comments'):
            for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
                comment.extract()

        if options.get('remove_empty_tags'):
            for tag in list(soup.find_all()):
                if tag.name not in {'html', 'head', 'body', 'meta', 'link', 'img', 'br', 'hr', 'input'}:
                    if not tag.get_text(strip=True) and not tag.find(True):
                        tag.decompose()

        custom_css = str(options.get('custom_css') or '').strip()
        if custom_css and not remove_css:
            self._append_style(soup, custom_css)

        page_size = str(options.get('page_size') or '').strip()
        orientation = str(options.get('orientation') or '').strip().lower()
        if page_size or orientation:
            normalized_size = page_size if page_size in {'A3', 'A4', 'Letter', 'Legal'} else 'A4'
            is_landscape = orientation in {'landscape', '横向', '橫向'}
            self._append_style(
                soup,
                f'@page {{ size: {normalized_size} '
                f'{"landscape" if is_landscape else "portrait"}; margin: 10mm; }}'
            )

        background_color = normalize_hex_color(options.get('background_color'), '')
        if background_color:
            self._append_style(
                soup,
                '* { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } '
                f'@page {{ background: {background_color}; }} '
                f'html, body {{ background: {background_color} !important; min-height: 100vh; }} '
                f'body::before {{ content: ""; position: fixed; inset: 0; background: {background_color}; z-index: -1; }}'
            )

        if not options.get('code_mode') and options.get('fit_to_page_width', True) is not False:
            self._append_style(soup, self.PRINT_FIT_CSS)

        if soup.head:
            charset_meta = soup.head.find('meta', attrs={'charset': True})
            if charset_meta:
                charset_meta['charset'] = 'utf-8'
            else:
                meta = soup.new_tag('meta')
                meta['charset'] = 'utf-8'
                soup.head.insert(0, meta)

        result = str(soup)
        if options.get('compress_html'):
            result = re.sub(r'>\s+<', '><', result)
            result = re.sub(r'[ \t]+', ' ', result)
        return result

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
            html_content = read_text_file(input_path, options.get('encoding'))
            prepared_html = self._prepare_html_content(html_content, options)
            render_input_path = output_path + '.render.html'
            with open(render_input_path, 'w', encoding='utf-8') as render_file:
                render_file.write(prepared_html)
            input_uri = Path(render_input_path).resolve().as_uri()
            
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

            page_range = options.get('page_range')
            if page_range:
                self._apply_page_range(output_path, str(page_range))

            self.update_progress(input_path, 100)
            
            # Get file size
            size = os.path.getsize(output_path)
            
            response = {
                'success': True,
                'output_path': output_path,
                'size': size,
                'method': 'browser_print'
            }
            try:
                os.remove(render_input_path)
            except Exception:
                pass
            return response
            
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
        """将 HTML 源码转换为 PDF（代码格式），用浏览器打印以稳定支持中文字体。"""
        import html

        self.update_progress(input_path, 20)

        html_code = self._prepare_html_content(
            read_text_file(input_path, options.get('encoding')),
            options
        )
        lines = html_code.split('\n')
        code_rows = '\n'.join(
            '<tr>'
            f'<td class="line-no">{index}</td>'
            f'<td class="line-code"><pre>{html.escape(line) or " "}</pre></td>'
            '</tr>'
            for index, line in enumerate(lines, start=1)
        )

        code_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            margin: 0;
            background: #ffffff;
            color: #111111;
            font-family: "Noto Sans CJK SC", "Microsoft YaHei", "SimSun", "DejaVu Sans Mono", Consolas, monospace;
            font-size: 11px;
            line-height: 1.45;
        }}
        table.code {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}
        .line-no {{
            width: 42px;
            padding: 0 8px 0 0;
            color: #666666;
            text-align: right;
            vertical-align: top;
            border-right: 1px solid #d0d0d0;
            user-select: none;
        }}
        .line-code {{
            padding-left: 8px;
            vertical-align: top;
        }}
        pre {{
            margin: 0;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            word-break: break-word;
            font-family: inherit;
        }}
    </style>
</head>
<body>
    <table class="code">{code_rows}</table>
</body>
</html>'''

        render_input_path = output_path + '.code.html'
        try:
            with open(render_input_path, 'w', encoding='utf-8') as render_file:
                render_file.write(code_html)

            render_options = {
                'code_mode': False,
                'page_size': options.get('page_size'),
                'orientation': options.get('orientation'),
                'background_color': options.get('background_color') or '#ffffff',
                'page_range': options.get('page_range'),
            }
            result = self.convert(render_input_path, output_path, **render_options)
            result['method'] = 'code_mode_browser_print'
            self.update_progress(input_path, 100)
            return result
        finally:
            try:
                os.remove(render_input_path)
            except Exception:
                pass
