from .base import BaseConverter
from typing import Dict, Any


class TxtToHexConverter(BaseConverter):
    """TXT 到十六进制转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['txt', 'hex']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将文本转换为十六进制表示"""
        try:
            self.validate_input(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 格式选项
            format_type = options.get('format', 'spaced')  # spaced, continuous, dump
            uppercase = options.get('uppercase', True)
            
            if format_type == 'dump':
                # 类似 hexdump 的格式
                result = self._hex_dump(text.encode('utf-8'), uppercase)
            else:
                hex_chars = []
                for char in text:
                    for byte in char.encode('utf-8'):
                        hex_val = format(byte, '02X' if uppercase else '02x')
                        hex_chars.append(hex_val)
                
                if format_type == 'continuous':
                    result = ''.join(hex_chars)
                else:  # spaced
                    result = ' '.join(hex_chars)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path)
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"TXT to Hex conversion failed: {str(e)}")
    
    def _hex_dump(self, data: bytes, uppercase: bool) -> str:
        """生成 hexdump 格式输出"""
        lines = []
        fmt = '%02X' if uppercase else '%02x'
        
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            
            # 偏移量
            offset = format(i, '08x')
            
            # 十六进制部分
            hex_part = ' '.join(fmt % b for b in chunk)
            hex_part = hex_part.ljust(48)
            
            # ASCII 部分
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            
            lines.append(f'{offset}  {hex_part}  |{ascii_part}|')
        
        return '\n'.join(lines)
