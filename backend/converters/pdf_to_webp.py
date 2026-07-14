import fitz  # PyMuPDF
import os
import zipfile
from PIL import Image
from .base import BaseConverter
from typing import Dict, Any


class PdfToWebpConverter(BaseConverter):
    """PDF 到 WEBP 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['webp']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 PDF 转换为 WEBP"""
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
            
            temp_files = []
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            output_dir = os.path.dirname(output_path) or os.getcwd()
            
            zoom = options.get('zoom', 2.0)
            quality = options.get('quality', 85)
            mat = fitz.Matrix(zoom, zoom)
            
            processed_count = 0
            total_to_process = len(pages_to_process)
            
            for page_num in pages_to_process:
                if page_num < 0 or page_num >= page_count:
                    continue
                
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=mat)
                
                # 转换为 PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                if total_to_process == 1:
                    webp_filename = output_path
                else:
                    webp_filename = os.path.join(output_dir, f"{base_name}_page_{page_num+1}.webp")
                
                img.save(webp_filename, 'WEBP', quality=quality)
                temp_files.append(webp_filename)
                processed_count += 1
            
            doc.close()
            
            # 多页打包 ZIP
            final_output = output_path
            if total_to_process > 1:
                final_output = os.path.splitext(output_path)[0] + ".zip"
                with zipfile.ZipFile(final_output, 'w') as zf:
                    for f in temp_files:
                        zf.write(f, os.path.basename(f))
                        os.remove(f)
            
            return {
                'success': True,
                'output_path': final_output,
                'size': self.get_output_size(final_output),
                'page_count': processed_count
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"PDF to WEBP conversion failed: {str(e)}")
