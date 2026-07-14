import os
import shutil
import tempfile
from typing import Dict, Any
from .base import BaseConverter
from .ppt_to_pdf import PptToPdfConverter
from .pdf_to_image import PdfToImageConverter

class PptToImageConverter(BaseConverter):
    """PPT 转图片转换器 (通过 PDF 中转)"""
    
    def __init__(self):
        super().__init__()
        self.ppt_to_pdf = PptToPdfConverter()
        self.pdf_to_image = PdfToImageConverter()
        
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        self.validate_input(input_path)
        self.update_progress(input_path, 5)
        
        # 默认选项
        if 'quality' not in options:
            options['quality'] = 95
        if 'auto_crop' not in options:
            options['auto_crop'] = True
            
        # 1. PPT -> PDF
        temp_pdf = output_path + ".temp.pdf"
        
        try:
            # 1. PPT -> PDF
            print(f"[PptToImage] Converting PPT to PDF: {temp_pdf}")
            
            # 设置 PPT 转 PDF 的进度回调
            def ppt_progress(path, progress):
                # 映射 5% - 50%
                final_progress = 5 + int(progress * 0.45)
                self.update_progress(input_path, final_progress)
                
            self.ppt_to_pdf.progress_callback = ppt_progress
            
            pdf_result = self.ppt_to_pdf.convert(input_path, temp_pdf)
            
            if not pdf_result.get('success'):
                raise Exception(f"PPT to PDF conversion failed: {pdf_result.get('error')}")
                
            self.update_progress(input_path, 50)
            
            # 2. PDF -> Image
            print(f"[PptToImage] Converting PDF to Image: {output_path}")
            
            # 设置 PDF 转 Image 的进度回调
            def img_progress(path, progress):
                # 映射 50% - 100%
                final_progress = 50 + int(progress * 0.5)
                self.update_progress(input_path, final_progress)
            
            self.pdf_to_image.progress_callback = img_progress
            
            # 传递选项（如 quality, merge, watermark 等）
            img_result = self.pdf_to_image.convert(temp_pdf, output_path, **options)
            
            return img_result
            
        finally:
            # 清理临时 PDF
            if os.path.exists(temp_pdf):
                try:
                    os.remove(temp_pdf)
                except:
                    pass
