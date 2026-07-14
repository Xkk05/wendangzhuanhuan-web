from .base import BaseConverter
from typing import Dict, Any


class TxtToAsciiConverter(BaseConverter):
    """TXT 到 ASCII Art 转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['txt']
        
        # ASCII 字符集（从暗到亮）
        self.ascii_chars = '@%#*+=-:. '
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将文本转换为 ASCII 艺术字"""
        try:
            self.validate_input(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            
            style = options.get('style', 'banner')
            
            if style == 'banner':
                result = self._create_banner(text)
            elif style == 'box':
                result = self._create_box(text)
            else:
                result = self._create_simple(text)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"TXT to ASCII conversion failed: {str(e)}")
    
    def _create_banner(self, text: str) -> str:
        """创建横幅样式"""
        lines = text.split('\n')
        max_len = max(len(line) for line in lines) if lines else 0
        
        result = []
        result.append('*' * (max_len + 4))
        for line in lines:
            result.append(f'* {line.ljust(max_len)} *')
        result.append('*' * (max_len + 4))
        
        return '\n'.join(result)
    
    def _create_box(self, text: str) -> str:
        """创建方框样式"""
        lines = text.split('\n')
        max_len = max(len(line) for line in lines) if lines else 0
        
        result = []
        result.append('┌' + '─' * (max_len + 2) + '┐')
        for line in lines:
            result.append(f'│ {line.ljust(max_len)} │')
        result.append('└' + '─' * (max_len + 2) + '┘')
        
        return '\n'.join(result)
    
    def _create_simple(self, text: str) -> str:
        """简单样式"""
        lines = text.split('\n')
        max_len = max(len(line) for line in lines) if lines else 0
        
        result = []
        result.append('=' * max_len)
        result.append(text)
        result.append('=' * max_len)
        
        return '\n'.join(result)
