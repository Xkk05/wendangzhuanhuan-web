#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
默认配置

所有转换器的默认配置项
"""

# ============================================
# 通用配置
# ============================================

COMMON_CONFIG = {
    'output_path': './output',           # 默认输出目录
    'progress_callback': None,           # 进度回调函数
}

# ============================================
# Word转换器配置
# ============================================

WORD_CONVERTER_CONFIG = {
    'output_format': 'docx',             # 输出格式: 'docx' 或 'doc'
    'extract_images': True,              # 提取图片
    'extract_tables': True,              # 提取表格
    'page_range': None,                  # 页面范围，如 '1-10,15,20'
}

# ============================================
# Excel转换器配置
# ============================================

EXCEL_CONVERTER_CONFIG = {
    'output_format': 'xlsx',             # 输出格式: 'xlsx' 或 'xls'
    'mode': 'extract',                   # PDF转换模式: 'extract' 或 'ocr'
}

# ============================================
# PPT转换器配置
# ============================================

PPT_CONVERTER_CONFIG = {
    'output_format': 'pptx',             # 输出格式: 'pptx' 或 'ppt'
}

# ============================================
# Image转换器配置
# ============================================

IMAGE_CONVERTER_CONFIG = {
    'output_format': 'png',              # 格式: 'png', 'jpg', 'bmp', 'webp', 'gif'
    'quality': 'high',                   # 质量: 'ultra', 'high', 'medium'
    'dpi': 200,                          # DPI分辨率
    'transparent': False,                # 透明背景
    'lossless': False,                   # 无损压缩
}

# ============================================
# PDF转换器配置
# ============================================

PDF_CONVERTER_CONFIG = {
    'prefer_office': True,               # 优先使用Office COM（Windows）
    'image_quality': 95,                 # 图片质量（1-100）
    'paper_size': 'A4',                  # 纸张大小
}

# ============================================
# HTML转换器配置
# ============================================

HTML_CONVERTER_CONFIG = {
    'include_images': True,              # 包含图片
    'include_styles': True,              # 包含样式
}

# ============================================
# Markdown转换器配置
# ============================================

MARKDOWN_CONVERTER_CONFIG = {}

# ============================================
# Text转换器配置
# ============================================

TEXT_CONVERTER_CONFIG = {
    'encoding': 'utf-8',                 # 文本编码
}

# ============================================
# OCR服务配置
# ============================================

OCR_CONFIG = {
    'model': 'auto',                     # 模型: 'auto', 'deepseek-ocr', 'paddleocr-vl', 'pp-structurev3'
    'has_seal': False,                   # 识别印章
    'has_formula': False,                # 识别公式
    'has_chart': False,                  # 识别图表
    'target_format': 'word',             # 输出格式: 'word' 或 'excel'
    'output_dir': './output',            # 输出目录
}

# ============================================
# PDF工具配置
# ============================================

PDF_TOOLS_CONFIG = {
    'image_quality': 75,                 # 压缩时的图片质量
    'pages_per_file': 10,                # 拆分时每个文件的页数
}

# ============================================
# Office转PDF配置
# ============================================

OFFICE_TO_PDF_CONFIG = {
    'prefer_office': True,               # 优先使用Office COM
    'libreoffice_path': None,            # LibreOffice路径（自动检测）
}


def get_default_config(converter_type='word'):
    """
    获取指定转换器的默认配置
    
    Args:
        converter_type: 转换器类型
            - 'word', 'excel', 'ppt', 'image', 'pdf', 
            - 'html', 'markdown', 'text', 
            - 'ocr', 'pdf_tools', 'office_to_pdf'
    
    Returns:
        dict: 默认配置字典
    """
    config_map = {
        'word': WORD_CONVERTER_CONFIG,
        'excel': EXCEL_CONVERTER_CONFIG,
        'ppt': PPT_CONVERTER_CONFIG,
        'image': IMAGE_CONVERTER_CONFIG,
        'pdf': PDF_CONVERTER_CONFIG,
        'html': HTML_CONVERTER_CONFIG,
        'markdown': MARKDOWN_CONVERTER_CONFIG,
        'text': TEXT_CONVERTER_CONFIG,
        'ocr': OCR_CONFIG,
        'pdf_tools': PDF_TOOLS_CONFIG,
        'office_to_pdf': OFFICE_TO_PDF_CONFIG,
    }
    
    return config_map.get(converter_type.lower(), {}).copy()


if __name__ == '__main__':
    # 测试配置
    print("默认配置示例:")
    print("\nWord转换器配置:")
    print(get_default_config('word'))
    
    print("\nOCR配置:")
    print(get_default_config('ocr'))
