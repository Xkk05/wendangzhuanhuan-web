"""
文档转换核心逻辑库
支持多种文档格式互转和OCR识别
"""

__version__ = '1.0.0'

from .core import (
    Converter,
    WordConverter,
    ExcelConverter,
    PPTConverter,
    ImageConverter,
    PDFConverter,
    HTMLConverter,
    MarkdownConverter,
    TextConverter,
)

from .ocr import (
    BaiduOCRService,
    OCRConversionService,
    OCRConfig,
    OCRPageResult,
    OCRWordGenerator,
    OCRExcelGenerator,
)

from .tools import (
    OfficeToPDF,
    PDFTools,
)

from .services import (
    MarkdownParser,
    RetryStrategy,
    PDFValidator,
    APIKeyManager,
)

__all__ = [
    # 核心转换器
    'Converter',
    'WordConverter',
    'ExcelConverter',
    'PPTConverter',
    'ImageConverter',
    'PDFConverter',
    'HTMLConverter',
    'MarkdownConverter',
    'TextConverter',
    
    # OCR服务
    'BaiduOCRService',
    'OCRConversionService',
    'OCRConfig',
    'OCRPageResult',
    'OCRWordGenerator',
    'OCRExcelGenerator',
    
    # 专用工具
    'OfficeToPDF',
    'PDFTools',
    
    # 辅助服务
    'MarkdownParser',
    'RetryStrategy',
    'PDFValidator',
    'APIKeyManager',
]
