#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
转换器基类
"""

from abc import ABC, abstractmethod
import os


class Converter(ABC):
    """转换器基类"""
    
    def __init__(self, output_path, config, progress_callback=None):
        self.output_path = output_path
        self.config = config
        self.progress_callback = progress_callback
        
        # 确保输出目录存在
        os.makedirs(output_path, exist_ok=True)
    
    def update_progress(self, file_path, progress):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(file_path, progress)
    
    @abstractmethod
    def convert(self, file_path):
        """
        转换文件
        
        Args:
            file_path: 源文件路径
            
        Returns:
            dict: {'success': bool, 'output_file': str, 'error': str}
        """
        pass
    
    def get_output_filename(self, input_file, extension):
        """生成输出文件名"""
        import re
        
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        
        # 移除Windows非法字符
        base_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)
        # 移除控制字符
        base_name = re.sub(r'[\x00-\x1f]', '', base_name)
        base_name = base_name.strip().strip('.')
        if not base_name:
            base_name = "untitled"
        
        # 确保扩展名不包含点号
        if extension.startswith('.'):
            extension = extension[1:]
        
        output_file = os.path.join(self.output_path, f"{base_name}.{extension}")
        
        # 如果文件已存在，添加序号
        counter = 1
        while os.path.exists(output_file):
            output_file = os.path.join(self.output_path, f"{base_name}_{counter}.{extension}")
            counter += 1
        
        return output_file
