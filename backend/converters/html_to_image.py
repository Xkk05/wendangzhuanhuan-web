import os
import logging
from .base import BaseConverter
from .html_to_pdf import HtmlToPdfConverter
from .pdf_to_image import PdfToImageConverter
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HtmlToImageConverter(BaseConverter):
    """HTML 到图片转换器（基于 PDF 中转）
    
    策略：
    1. HTML -> PDF (使用浏览器无头打印，保证渲染效果)
    2. PDF -> Image (使用 PyMuPDF 转图片，支持长图合并)
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['png', 'jpg', 'jpeg']
        self.pdf_converter = HtmlToPdfConverter()
        self.image_converter = PdfToImageConverter()

    @staticmethod
    def _is_visually_blank_page(page) -> bool:
        import fitz

        if page.get_text('text').strip() or page.get_images(full=True):
            return False
        pixmap = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2), colorspace=fitz.csGRAY, alpha=False)
        samples = pixmap.samples
        if not samples:
            return True
        return max(samples) - min(samples) <= 3

    def _trim_trailing_blank_pages(self, pdf_path: str) -> int:
        import fitz

        document = fitz.open(pdf_path)
        original_count = len(document)
        try:
            keep_count = original_count
            while keep_count > 1 and self._is_visually_blank_page(document[keep_count - 1]):
                keep_count -= 1
            if keep_count == len(document):
                return 0

            trimmed_path = pdf_path + '.trimmed.pdf'
            trimmed = fitz.open()
            try:
                trimmed.insert_pdf(document, from_page=0, to_page=keep_count - 1)
                trimmed.save(trimmed_path)
            finally:
                trimmed.close()
        finally:
            document.close()

        os.replace(trimmed_path, pdf_path)
        return original_count - keep_count
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 HTML 转换为图片"""
        temp_pdf = None
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 5)
            
            # 1. HTML 转 PDF
            # 使用与输出文件相同的目录，防止权限问题
            output_dir = os.path.dirname(output_path) or os.getcwd()
            temp_pdf_name = f"temp_{os.path.basename(input_path)}.pdf"
            temp_pdf = os.path.join(output_dir, temp_pdf_name)
            
            logger.info(f"Converting HTML to temporary PDF: {temp_pdf}")
            
            # 强制使用渲染模式（codeMode=False），因为转图片通常是为了看效果
            pdf_options = options.copy()
            pdf_options['code_mode'] = False
            
            # 调用 PDF 转换器
            pdf_result = self.pdf_converter.convert(input_path, temp_pdf, **pdf_options)
            
            if not pdf_result.get('success'):
                raise Exception("HTML to PDF conversion failed")

            self._trim_trailing_blank_pages(temp_pdf)
                
            self.update_progress(input_path, 50)
            
            # 2. PDF 转 图片
            logger.info(f"Converting PDF to Image: {output_path}")
            
            # 确保开启合并模式 (merge=True)，这样多页 PDF 会变成一张长图
            image_options = options.copy()
            image_options['merge'] = True
            
            image_result = self.image_converter.convert(temp_pdf, output_path, **image_options)
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'method': 'browser_print_via_pdf'
            }
            
        except Exception as e:
            logger.error(f"HTML to Image conversion failed: {str(e)}")
            self.cleanup_on_error(output_path)
            raise Exception(f"HTML to Image conversion failed: {str(e)}")
        finally:
            # 清理临时 PDF 文件
            if temp_pdf and os.path.exists(temp_pdf):
                try:
                    os.remove(temp_pdf)
                except Exception as e:
                    logger.warning(f"Failed to remove temporary PDF {temp_pdf}: {e}")
