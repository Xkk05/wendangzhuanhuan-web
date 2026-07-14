import fitz  # PyMuPDF
import os
import zipfile
import html
import uuid
from .base import BaseConverter
from typing import Dict, Any


class PdfToEpubConverter(BaseConverter):
    """PDF 到 EPUB 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['epub']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 PDF 转换为 EPUB"""
        try:
            self.validate_input(input_path)
            
            doc = fitz.open(input_path)
            book_id = str(uuid.uuid4())
            title = options.get('title', os.path.splitext(os.path.basename(input_path))[0])
            author = options.get('author', doc.metadata.get('author', 'Unknown'))
            
            # 解析页面范围
            raw_page_range = options.get('pdf_page_range') or options.get('page_range')
            pages = self.parse_page_range(raw_page_range, total_pages=doc.page_count)
            
            # 确定要处理的页面
            if pages is None:
                pages_to_process = range(doc.page_count)
            else:
                pages_to_process = pages
            
            # 提取每页内容
            chapters = []
            for page_num in pages_to_process:
                if page_num < 0 or page_num >= doc.page_count:
                    continue
                    
                page = doc.load_page(page_num)
                text = page.get_text('text').strip()
                if text:
                    paragraphs = [html.escape(p) for p in text.split('\n') if p.strip()]
                    chapters.append({
                        'title': f'Page {page_num + 1}',
                        'content': paragraphs
                    })
            
            doc.close()
            
            if not chapters:
                chapters = [{'title': 'Content', 'content': ['(Empty document)']}]
            
            # 创建 EPUB
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
                epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
                
                container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
                epub.writestr('META-INF/container.xml', container_xml)
                
                manifest_items = []
                spine_items = []
                for i in range(len(chapters)):
                    manifest_items.append(f'    <item id="chapter{i}" href="chapter{i}.xhtml" media-type="application/xhtml+xml"/>')
                    spine_items.append(f'    <itemref idref="chapter{i}"/>')
                
                content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{book_id}</dc:identifier>
    <dc:title>{html.escape(title)}</dc:title>
    <dc:creator>{html.escape(author)}</dc:creator>
    <dc:language>zh-CN</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
{chr(10).join(manifest_items)}
  </manifest>
  <spine>
{chr(10).join(spine_items)}
  </spine>
</package>'''
                epub.writestr('OEBPS/content.opf', content_opf)
                
                nav_items = [f'      <li><a href="chapter{i}.xhtml">{html.escape(c["title"])}</a></li>' for i, c in enumerate(chapters)]
                nav_xhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <h1>目录</h1>
    <ol>
{chr(10).join(nav_items)}
    </ol>
  </nav>
</body>
</html>'''
                epub.writestr('OEBPS/nav.xhtml', nav_xhtml)
                
                for i, chapter in enumerate(chapters):
                    paragraphs = '\n'.join([f'<p>{p}</p>' for p in chapter['content']])
                    chapter_xhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{html.escape(chapter["title"])}</title>
  <style>body {{ font-family: serif; line-height: 1.6; padding: 1em; }}</style>
</head>
<body>
  <h1>{html.escape(chapter["title"])}</h1>
  {paragraphs}
</body>
</html>'''
                    epub.writestr(f'OEBPS/chapter{i}.xhtml', chapter_xhtml)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'chapters': len(chapters)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"PDF to EPUB conversion failed: {str(e)}")
