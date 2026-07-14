# backend/utils/validator.py
from typing import List, Optional

class Validator:
    """参数验证器"""
    
    @staticmethod
    def validate_target_format(target_format: str, allowed_formats: List[str]) -> str:
        if not target_format:
            raise ValueError("Target format is required")
        
        target_format = target_format.lower().strip()
        if target_format not in allowed_formats:
            raise ValueError(f"Unsupported target format: {target_format}. Allowed: {allowed_formats}")
        
        return target_format

    @staticmethod
    def validate_json_options(options: dict) -> dict:
        """验证并清理 JSON 转换选项"""
        cleaned = {}
        if 'indent' in options:
            try:
                indent = int(options['indent'])
                cleaned['indent'] = max(1, min(10, indent))
            except (ValueError, TypeError):
                cleaned['indent'] = 2
        
        if 'sort_keys' in options:
            cleaned['sort_keys'] = bool(options['sort_keys'])
            
        return cleaned
