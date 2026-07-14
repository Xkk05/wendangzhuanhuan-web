#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API密钥管理模块
负责百度千帆API密钥的验证、存储和读取
需求: 1.1, 1.2, 1.3, 1.4
"""

import os
import json
import re
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class APIKeyValidationResult:
    """API密钥验证结果"""
    is_valid: bool
    error_message: Optional[str] = None


class APIKeyManager:
    """
    API密钥管理器
    
    负责:
    - 验证API密钥格式 (bce-v3/ALTAK- 前缀)
    - 安全地持久化API密钥到本地存储
    - 读取已保存的API密钥
    """
    
    # 有效的API密钥前缀
    VALID_PREFIXES = ('bce-v3/', 'ALTAK-')
    
    # 默认配置文件路径
    DEFAULT_CONFIG_DIR = 'data'
    DEFAULT_CONFIG_FILE = 'ocr_config.json'
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化API密钥管理器
        
        Args:
            config_dir: 配置文件目录路径，默认为 backend/data
        """
        if config_dir is None:
            # 获取backend目录的绝对路径
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(backend_dir, self.DEFAULT_CONFIG_DIR)
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, self.DEFAULT_CONFIG_FILE)
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
    
    def validate_format(self, api_key: str) -> APIKeyValidationResult:
        """
        验证API密钥格式
        
        有效格式:
        - bce-v3/xxx... (百度BCE V3格式)
        - ALTAK-xxx... (百度ALTAK格式)
        
        Args:
            api_key: 待验证的API密钥
            
        Returns:
            APIKeyValidationResult: 验证结果
        """
        if not api_key:
            return APIKeyValidationResult(
                is_valid=False,
                error_message="API密钥不能为空"
            )
        
        if not isinstance(api_key, str):
            return APIKeyValidationResult(
                is_valid=False,
                error_message="API密钥必须是字符串类型"
            )
        
        # 去除首尾空白
        api_key = api_key.strip()
        
        if not api_key:
            return APIKeyValidationResult(
                is_valid=False,
                error_message="API密钥不能为空白字符串"
            )
        
        # 检查是否以有效前缀开头
        has_valid_prefix = any(api_key.startswith(prefix) for prefix in self.VALID_PREFIXES)
        
        if not has_valid_prefix:
            return APIKeyValidationResult(
                is_valid=False,
                error_message=f"API密钥格式无效，必须以 {' 或 '.join(self.VALID_PREFIXES)} 开头"
            )
        
        # 检查前缀后是否有实际内容
        for prefix in self.VALID_PREFIXES:
            if api_key.startswith(prefix):
                key_content = api_key[len(prefix):]
                if not key_content:
                    return APIKeyValidationResult(
                        is_valid=False,
                        error_message="API密钥内容不完整"
                    )
                break
        
        return APIKeyValidationResult(is_valid=True)
    
    def save(self, api_key: str, validate: bool = True) -> Tuple[bool, Optional[str]]:
        """
        保存API密钥到本地存储
        
        Args:
            api_key: 要保存的API密钥
            validate: 是否在保存前验证格式，默认为True
            
        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误信息)
        """
        if validate:
            validation_result = self.validate_format(api_key)
            if not validation_result.is_valid:
                return False, validation_result.error_message
        
        try:
            # 读取现有配置
            config = self._load_config()
            
            # 更新API密钥
            config['api_key'] = api_key.strip()
            
            # 保存配置
            self._save_config(config)
            
            return True, None
            
        except Exception as e:
            return False, f"保存API密钥失败: {str(e)}"
    
    def load(self) -> Optional[str]:
        """
        从本地存储读取API密钥
        
        Returns:
            Optional[str]: API密钥，如果不存在则返回None
        """
        try:
            config = self._load_config()
            return config.get('api_key')
        except Exception:
            return None
    
    def delete(self) -> Tuple[bool, Optional[str]]:
        """
        删除已保存的API密钥
        
        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误信息)
        """
        try:
            config = self._load_config()
            
            if 'api_key' in config:
                del config['api_key']
                self._save_config(config)
            
            return True, None
            
        except Exception as e:
            return False, f"删除API密钥失败: {str(e)}"
    
    def has_api_key(self) -> bool:
        """
        检查是否已配置API密钥
        
        Returns:
            bool: 是否已配置有效的API密钥
        """
        api_key = self.load()
        if not api_key:
            return False
        
        validation_result = self.validate_format(api_key)
        return validation_result.is_valid
    
    def get_validation_error(self) -> Optional[str]:
        """
        获取当前API密钥的验证错误信息
        
        Returns:
            Optional[str]: 错误信息，如果密钥有效则返回None
        """
        api_key = self.load()
        
        if not api_key:
            return "请先配置百度千帆API密钥"
        
        validation_result = self.validate_format(api_key)
        
        if not validation_result.is_valid:
            return validation_result.error_message
        
        return None
    
    def _load_config(self) -> dict:
        """
        加载配置文件
        
        Returns:
            dict: 配置字典
        """
        if not os.path.exists(self.config_file):
            return {}
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save_config(self, config: dict) -> None:
        """
        保存配置文件
        
        Args:
            config: 配置字典
        """
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)


# 全局单例实例
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """
    获取API密钥管理器单例实例
    
    Returns:
        APIKeyManager: API密钥管理器实例
    """
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
