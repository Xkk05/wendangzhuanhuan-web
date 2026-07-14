"""OCR服务模块"""

from .ocr_service import BaiduOCRService
from .ocr_conversion_service import OCRConversionService, OCRConfig, OCRPageResult
from .ocr_word_generator import OCRWordGenerator
from .ocr_excel_generator import OCRExcelGenerator

__all__ = [
    'BaiduOCRService',
    'OCRConversionService',
    'OCRConfig',
    'OCRPageResult',
    'OCRWordGenerator',
    'OCRExcelGenerator',
]
