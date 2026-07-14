import fitz  # PyMuPDF
import json
from .base import BaseConverter
from typing import Dict, Any


class PdfToJsonConverter(BaseConverter):
    """PDF 到 JSON 转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加进度回调
    2. 添加更详细的文本块信息（字体、大小、颜色）
    3. 添加表格检测
    4. 添加链接提取
    5. 更好的错误处理
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['json']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 PDF 转换为 JSON（增强版）"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 5)
            
            doc = fitz.open(input_path)
            total_pages = doc.page_count
            
            if total_pages == 0:
                doc.close()
                raise Exception("PDF file is empty")
            
            self.update_progress(input_path, 10)
            
            # 提取详细选项
            include_fonts = options.get('include_fonts', True)
            include_links = options.get('include_links', True)
            include_tables = options.get('include_tables', True)
            
            # 解析页面范围
            raw_page_range = options.get('pdf_page_range') or options.get('page_range')
            pages = self.parse_page_range(raw_page_range, total_pages=total_pages)
            
            # 确定要处理的页面
            if pages is None:
                pages_to_process = range(total_pages)
            else:
                pages_to_process = pages
            
            result = {
                'metadata': {
                    'title': doc.metadata.get('title', ''),
                    'author': doc.metadata.get('author', ''),
                    'subject': doc.metadata.get('subject', ''),
                    'creator': doc.metadata.get('creator', ''),
                    'producer': doc.metadata.get('producer', ''),
                    'creation_date': doc.metadata.get('creationDate', ''),
                    'modification_date': doc.metadata.get('modDate', ''),
                    'page_count': total_pages,
                    'processed_pages': len(pages_to_process),
                    'encrypted': doc.is_encrypted,
                    'format': 'PDF'
                },
                'pages': []
            }
            
            processed_count = 0
            total_to_process = len(pages_to_process)
            
            for page_num in pages_to_process:
                if page_num < 0 or page_num >= total_pages:
                    continue
                    
                page = doc.load_page(page_num)
                
                page_data = {
                    'page_number': page_num + 1,
                    'width': round(page.rect.width, 2),
                    'height': round(page.rect.height, 2),
                    'rotation': page.rotation,
                    'text': page.get_text('text'),
                    'blocks': []
                }
                
                # 提取文本块信息（增强版）
                blocks = page.get_text('dict')['blocks']
                for block in blocks:
                    if block['type'] == 0:  # 文本块
                        block_data = {
                            'type': 'text',
                            'bbox': [round(x, 2) for x in block['bbox']],
                            'lines': []
                        }
                        
                        for line in block.get('lines', []):
                            line_data = {
                                'text': '',
                                'bbox': [round(x, 2) for x in line['bbox']],
                                'spans': []
                            }
                            
                            for span in line.get('spans', []):
                                line_data['text'] += span['text']
                                
                                if include_fonts:
                                    span_data = {
                                        'text': span['text'],
                                        'font': span.get('font', ''),
                                        'size': round(span.get('size', 0), 2),
                                        'flags': span.get('flags', 0),
                                        'color': span.get('color', 0)
                                    }
                                    line_data['spans'].append(span_data)
                            
                            block_data['lines'].append(line_data)
                        
                        page_data['blocks'].append(block_data)
                    
                    elif block['type'] == 1:  # 图片块
                        page_data['blocks'].append({
                            'type': 'image',
                            'bbox': [round(x, 2) for x in block['bbox']],
                            'width': round(block.get('width', 0), 2),
                            'height': round(block.get('height', 0), 2)
                        })
                
                # 提取链接
                if include_links:
                    links = []
                    for link in page.get_links():
                        if 'uri' in link:
                            links.append({
                                'type': 'uri',
                                'uri': link['uri'],
                                'bbox': [round(x, 2) for x in link['from']]
                            })
                    if links:
                        page_data['links'] = links
                
                # 检测表格
                if include_tables:
                    try:
                        tables = page.find_tables()
                        if tables:
                            page_data['tables'] = len(tables)
                    except:
                        pass
                
                result['pages'].append(page_data)
                
                # 更新进度 (10% ~ 85%)
                processed_count += 1
                progress = 10 + int((processed_count / total_to_process) * 75)
                self.update_progress(input_path, progress)
            
            doc.close()
            self.update_progress(input_path, 90)
            
            # 保存 JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'total_pages': total_pages
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"PDF to JSON conversion failed: {str(e)}")
