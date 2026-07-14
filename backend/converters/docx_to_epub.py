import os
import zipfile
import html
import uuid
from docx import Document
from .base import BaseConverter
from typing import Dict, Any


class DocxToEpubConverter(BaseConverter):
    """DOCX 到 EPUB 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['epub']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 DOCX 转换为 EPUB"""
        try:
            self.validate_input(input_path)
            
            doc = Document(input_path)
            book_id = str(uuid.uuid4())
            title = options.get('title', os.path.splitext(os.path.basename(input_path))[0])
            author = options.get('author', 'Unknown')
            
            # 提取段落内容
            chapters = []
            current_chapter = {'title': 'Chapter 1', 'content': []}
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                # 简单判断标题（根据样式或字体大小）
                if para.style and 'Heading' in para.style.name:
                    if current_chapter['content']:
                        chapters.append(current_chapter)
                    current_chapter = {'title': text, 'content': []}
                else:
                    current_chapter['content'].append(html.escape(text))
            
            if current_chapter['content']:
                chapters.append(current_chapter)
            
            if not chapters:
                chapters = [{'title': 'Content', 'content': ['(Empty document)']}]
            
            # 创建 EPUB 文件
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
                # mimetype (必须是第一个文件，不压缩)
                epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
                
                # META-INF/container.xml
                container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
                epub.writestr('META-INF/container.xml', container_xml)
                
                # OEBPS/content.opf
                manifest_items = []
                spine_items = []
                for i, chapter in enumerate(chapters):
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
                
                # OEBPS/nav.xhtml (导航)
                nav_items = []
                for i, chapter in enumerate(chapters):
                    nav_items.append(f'      <li><a href="chapter{i}.xhtml">{html.escape(chapter["title"])}</a></li>')
                
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
                
                # 章节文件
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
            raise Exception(f"DOCX to EPUB conversion failed: {str(e)}")
