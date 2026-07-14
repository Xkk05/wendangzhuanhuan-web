import fitz  # PyMuPDF
import os
from PIL import Image
from .base import BaseConverter
from typing import Dict, Any


class PdfToGifConverter(BaseConverter):
    """PDF 到 GIF 转换器 - 多页 PDF 转为动画 GIF"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['gif']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 PDF 转换为 GIF 动画"""
        try:
            self.validate_input(input_path)
            
            doc = fitz.open(input_path)
            page_count = doc.page_count
            
            # 解析页面范围
            raw_page_range = options.get('pdf_page_range') or options.get('page_range')
            pages = self.parse_page_range(raw_page_range, total_pages=page_count)
            
            # 确定要处理的页面
            if pages is None:
                pages_to_process = range(page_count)
            else:
                pages_to_process = pages
            
            # 配置参数
            zoom = options.get('zoom', 1.5)
            duration = options.get('duration', 1000)  # 每帧持续时间(毫秒)
            loop = options.get('loop', 0)  # 0 表示无限循环
            
            mat = fitz.Matrix(zoom, zoom)
            images = []
            
            for page_num in pages_to_process:
                if page_num < 0 or page_num >= page_count:
                    continue
                
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=mat)
                
                # 转换为 PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            
            doc.close()
            
            if not images:
                raise Exception("No pages found in PDF or selected range")
            
            # 保存为 GIF
            images[0].save(
                output_path,
                save_all=True,
                append_images=images[1:] if len(images) > 1 else [],
                duration=duration,
                loop=loop
            )
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'page_count': len(images)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"PDF to GIF conversion failed: {str(e)}")
