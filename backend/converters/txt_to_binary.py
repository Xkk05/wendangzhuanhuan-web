from .base import BaseConverter
from typing import Dict, Any


class TxtToBinaryConverter(BaseConverter):
    """TXT 到二进制转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['txt', 'bin']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将文本转换为二进制表示"""
        try:
            self.validate_input(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 转换格式选项
            format_type = options.get('format', 'spaced')  # spaced, continuous, newline
            
            binary_chars = []
            for char in text:
                # 将每个字符转换为二进制
                binary = format(ord(char), '08b')
                binary_chars.append(binary)
            
            if format_type == 'continuous':
                result = ''.join(binary_chars)
            elif format_type == 'newline':
                result = '\n'.join(binary_chars)
            else:  # spaced
                result = ' '.join(binary_chars)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"TXT to Binary conversion failed: {str(e)}")
