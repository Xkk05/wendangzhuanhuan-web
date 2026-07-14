#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重试策略模块 - 实现指数退避和重试控制
需求: 10.2, 10.3
"""

import time
import functools
from typing import Callable, Optional, Set, TypeVar, Any
from enum import Enum


class ErrorCode(Enum):
    """错误类型枚举"""
    AUTH_ERROR = "AUTH_ERROR"           # API密钥无效
    NO_API_KEY = "NO_API_KEY"           # API密钥未配置
    RATE_LIMIT = "RATE_LIMIT"           # 频率限制
    SERVER_ERROR = "SERVER_ERROR"       # 服务器错误
    FILE_ERROR = "FILE_ERROR"           # 文件读取失败
    TIMEOUT = "TIMEOUT"                 # 网络超时
    FILE_TOO_LARGE = "FILE_TOO_LARGE"   # 文件过大
    OCR_ERROR = "OCR_ERROR"             # OCR识别失败
    NETWORK_ERROR = "NETWORK_ERROR"     # 网络错误


class OCRError(Exception):
    """OCR错误基类"""
    
    def __init__(self, message: str, error_code: ErrorCode, 
                 retryable: bool = False, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retryable = retryable
        self.details = details
    
    def to_dict(self) -> dict:
        return {
            "error": self.message,
            "error_code": self.error_code.value,
            "retryable": self.retryable,
            "details": self.details
        }


class RetryStrategy:
    """重试策略类"""
    
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # 秒
    
    # 可重试的错误类型
    RETRYABLE_ERRORS: Set[ErrorCode] = {
        ErrorCode.RATE_LIMIT,
        ErrorCode.SERVER_ERROR,
        ErrorCode.TIMEOUT,
        ErrorCode.NETWORK_ERROR
    }
    
    @staticmethod
    def exponential_backoff(attempt: int) -> float:
        """
        计算指数退避延迟时间
        
        Args:
            attempt: 当前重试次数（从0开始）
            
        Returns:
            float: 延迟时间（秒）
        """
        if attempt < 0:
            return RetryStrategy.BASE_DELAY
        return RetryStrategy.BASE_DELAY * (2 ** attempt)
    
    @staticmethod
    def should_retry(error_code: ErrorCode, attempt: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            error_code: 错误类型
            attempt: 当前重试次数（从0开始）
            
        Returns:
            bool: 是否应该重试
        """
        return (error_code in RetryStrategy.RETRYABLE_ERRORS and 
                attempt < RetryStrategy.MAX_RETRIES)
    
    @staticmethod
    def get_remaining_retries(attempt: int) -> int:
        """
        获取剩余重试次数
        
        Args:
            attempt: 当前重试次数
            
        Returns:
            int: 剩余重试次数
        """
        return max(0, RetryStrategy.MAX_RETRIES - attempt)


T = TypeVar('T')


def with_retry(
    max_retries: int = RetryStrategy.MAX_RETRIES,
    base_delay: float = RetryStrategy.BASE_DELAY,
    retryable_errors: Optional[Set[ErrorCode]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
) -> Callable:
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间
        retryable_errors: 可重试的错误类型集合
        on_retry: 重试回调函数 (attempt, exception, delay)
        
    Returns:
        装饰器函数
    """
    if retryable_errors is None:
        retryable_errors = RetryStrategy.RETRYABLE_ERRORS
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except OCRError as e:
                    last_exception = e
                    
                    # 检查是否可重试
                    if not e.retryable or e.error_code not in retryable_errors:
                        raise
                    
                    # 检查是否还有重试机会
                    if attempt >= max_retries:
                        raise
                    
                    # 计算延迟时间
                    delay = base_delay * (2 ** attempt)
                    
                    # 调用重试回调
                    if on_retry:
                        on_retry(attempt, e, delay)
                    
                    # 等待后重试
                    time.sleep(delay)
                    
                except Exception as e:
                    # 非OCRError异常，不重试
                    raise
            
            # 不应该到达这里，但为了类型安全
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")
        
        return wrapper
    return decorator


def classify_http_error(status_code: int, response_body: Optional[dict] = None) -> ErrorCode:
    """
    根据HTTP状态码分类错误
    
    Args:
        status_code: HTTP状态码
        response_body: 响应体
        
    Returns:
        ErrorCode: 错误类型
    """
    if status_code == 401 or status_code == 403:
        return ErrorCode.AUTH_ERROR
    elif status_code == 429:
        return ErrorCode.RATE_LIMIT
    elif status_code >= 500:
        return ErrorCode.SERVER_ERROR
    elif status_code == 408:
        return ErrorCode.TIMEOUT
    else:
        return ErrorCode.OCR_ERROR


def create_ocr_error_from_response(
    status_code: int, 
    response_body: Optional[dict] = None,
    original_error: Optional[str] = None
) -> OCRError:
    """
    根据HTTP响应创建OCRError
    
    Args:
        status_code: HTTP状态码
        response_body: 响应体
        original_error: 原始错误信息
        
    Returns:
        OCRError: OCR错误对象
    """
    error_code = classify_http_error(status_code, response_body)
    
    # 错误消息映射
    error_messages = {
        ErrorCode.AUTH_ERROR: "API密钥无效，请检查配置",
        ErrorCode.RATE_LIMIT: "请求过于频繁，正在重试...",
        ErrorCode.SERVER_ERROR: "服务暂时不可用，正在重试...",
        ErrorCode.TIMEOUT: "网络连接超时，请检查网络",
        ErrorCode.OCR_ERROR: "OCR识别失败"
    }
    
    message = error_messages.get(error_code, "未知错误")
    retryable = error_code in RetryStrategy.RETRYABLE_ERRORS
    
    return OCRError(
        message=message,
        error_code=error_code,
        retryable=retryable,
        details=original_error
    )


def create_file_error(message: str, details: Optional[str] = None) -> OCRError:
    """创建文件错误"""
    return OCRError(
        message=message,
        error_code=ErrorCode.FILE_ERROR,
        retryable=False,
        details=details
    )


def create_network_error(message: str, details: Optional[str] = None) -> OCRError:
    """创建网络错误"""
    return OCRError(
        message=message,
        error_code=ErrorCode.NETWORK_ERROR,
        retryable=True,
        details=details
    )


def create_timeout_error(message: str = "网络连接超时，请检查网络", 
                         details: Optional[str] = None) -> OCRError:
    """创建超时错误"""
    return OCRError(
        message=message,
        error_code=ErrorCode.TIMEOUT,
        retryable=True,
        details=details
    )
