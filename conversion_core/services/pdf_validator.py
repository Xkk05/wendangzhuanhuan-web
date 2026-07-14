#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF文件验证器 - 验证PDF文件格式和大小
需求: 2.2, 2.4
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationError(Enum):
    """验证错误类型"""
    INVALID_EXTENSION = "invalid_extension"
    FILE_NOT_FOUND = "file_not_found"
    FILE_TOO_LARGE = "file_too_large"
    EMPTY_FILE = "empty_file"


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    error: Optional[str] = None
    error_code: Optional[str] = None
    file_size_mb: float = 0.0


# 默认文件大小限制 (MB)
DEFAULT_MAX_FILE_SIZE_MB = 100  # 100MB


def validate_pdf_extension(file_path: str) -> bool:
    """
    验证文件扩展名是否为.pdf
    
    属性3: PDF文件格式验证
    对于任意文件路径，当文件扩展名不是`.pdf`时，文件验证函数应当拒绝该文件
    验证: 需求 2.2
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 扩展名是否为.pdf
    """
    if not file_path:
        return False
    
    # 获取文件扩展名（不区分大小写）
    _, ext = os.path.splitext(file_path)
    return ext.lower() == '.pdf'


def validate_file_size(file_path: str, max_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB) -> Dict:
    """
    验证文件大小是否在限制范围内
    
    需求 2.4: 若PDF文件超过50MB或10页，则OCR系统应当将文件拆分为较小的块进行处理
    
    Args:
        file_path: 文件路径
        max_size_mb: 最大文件大小（MB）
        
    Returns:
        dict: {valid: bool, size_mb: float, error: str}
    """
    try:
        if not os.path.exists(file_path):
            return {
                "valid": False,
                "size_mb": 0.0,
                "error": "文件不存在"
            }
        
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        if file_size_bytes == 0:
            return {
                "valid": False,
                "size_mb": 0.0,
                "error": "文件为空"
            }
        
        if file_size_mb > max_size_mb:
            return {
                "valid": False,
                "size_mb": file_size_mb,
                "error": f"文件大小({file_size_mb:.2f}MB)超过限制({max_size_mb}MB)"
            }
        
        return {
            "valid": True,
            "size_mb": file_size_mb,
            "error": None
        }
        
    except Exception as e:
        return {
            "valid": False,
            "size_mb": 0.0,
            "error": f"无法读取文件大小: {str(e)}"
        }


def validate_pdf_file(file_path: str, max_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB) -> ValidationResult:
    """
    完整验证PDF文件（扩展名 + 大小）
    
    需求 2.2: 当用户通过拖放或文件选择器添加文件时，OCR系统应当验证文件为PDF格式
    需求 2.4: 若PDF文件超过50MB或10页，则OCR系统应当将文件拆分为较小的块进行处理
    
    Args:
        file_path: 文件路径
        max_size_mb: 最大文件大小（MB）
        
    Returns:
        ValidationResult: 验证结果
    """
    # 检查文件是否存在
    if not file_path:
        return ValidationResult(
            valid=False,
            error="文件路径为空",
            error_code=ValidationError.FILE_NOT_FOUND.value
        )
    
    if not os.path.exists(file_path):
        return ValidationResult(
            valid=False,
            error=f"文件不存在: {file_path}",
            error_code=ValidationError.FILE_NOT_FOUND.value
        )
    
    # 验证扩展名
    if not validate_pdf_extension(file_path):
        _, ext = os.path.splitext(file_path)
        return ValidationResult(
            valid=False,
            error=f"不支持的文件格式: {ext or '无扩展名'}，仅支持PDF文件",
            error_code=ValidationError.INVALID_EXTENSION.value
        )
    
    # 验证文件大小
    size_result = validate_file_size(file_path, max_size_mb)
    
    if not size_result["valid"]:
        error_code = ValidationError.FILE_TOO_LARGE.value
        if size_result["size_mb"] == 0:
            error_code = ValidationError.EMPTY_FILE.value
        
        return ValidationResult(
            valid=False,
            error=size_result["error"],
            error_code=error_code,
            file_size_mb=size_result["size_mb"]
        )
    
    return ValidationResult(
        valid=True,
        error=None,
        error_code=None,
        file_size_mb=size_result["size_mb"]
    )


class PDFValidator:
    """PDF文件验证器类"""
    
    def __init__(self, max_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB):
        """
        初始化验证器
        
        Args:
            max_size_mb: 最大文件大小（MB）
        """
        self.max_size_mb = max_size_mb
    
    def validate(self, file_path: str) -> ValidationResult:
        """
        验证PDF文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            ValidationResult: 验证结果
        """
        return validate_pdf_file(file_path, self.max_size_mb)
    
    def validate_extension(self, file_path: str) -> bool:
        """
        仅验证文件扩展名
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 扩展名是否为.pdf
        """
        return validate_pdf_extension(file_path)
    
    def validate_size(self, file_path: str) -> Dict:
        """
        仅验证文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 验证结果
        """
        return validate_file_size(file_path, self.max_size_mb)
    
    def is_valid_pdf(self, file_path: str) -> bool:
        """
        快速检查文件是否为有效PDF
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为有效PDF
        """
        result = self.validate(file_path)
        return result.valid
