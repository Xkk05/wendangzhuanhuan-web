from typing import Dict, Any
import os
import shutil
from .base import BaseConverter
from conversion_core.core.converter_ppt import PPTConverter
from conversion_core.config.default_config import PPT_CONVERTER_CONFIG

class ExcelToPptConverter(BaseConverter):
    """Excel 转 PPT 转换器"""
    
    def __init__(self):
        super().__init__()

    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        self.validate_input(input_path)
        self.update_progress(input_path, 5)
        
        # 准备配置
        config = PPT_CONVERTER_CONFIG.copy()
        if 'mode' in options:
            config['mode'] = options['mode']
            
        # 实例化 core converter
        output_dir = os.path.dirname(output_path)
        core_converter = PPTConverter(output_path=output_dir, config=config)
        
        # 设置 core converter 的回调
        def core_progress(path, progress):
            self.update_progress(path, progress)
        
        core_converter.progress_callback = core_progress
        
        # 调用核心转换逻辑
        result = core_converter._convert_excel_to_ppt(input_path)
        
        if result.get('success'):
            generated_file = result.get('output_file')
            if generated_file and os.path.exists(generated_file):
                # 如果生成的路径与目标路径不一致，移动文件
                if os.path.abspath(generated_file) != os.path.abspath(output_path):
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    shutil.move(generated_file, output_path)
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'size': self.get_output_size(output_path)
                }
            else:
                raise Exception("Conversion reported success but output file not found")
        else:
            raise Exception(result.get('error', 'Conversion failed'))
