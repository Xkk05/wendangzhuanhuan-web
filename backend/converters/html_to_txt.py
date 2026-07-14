import shutil
from bs4 import BeautifulSoup
from .base import BaseConverter
from typing import Dict, Any


class HtmlToTxtConverter(BaseConverter):
    """HTML 到 TXT 转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加进度回调
    2. 支持两种模式：源码模式 / 文本提取模式
    3. 更好的文本清理
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['txt']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 HTML 转换为 TXT"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 获取选项
            mode = options.get('mode', 'text')  # 'source' or 'text'
            
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            self.update_progress(input_path, 30)
            
            if mode == 'source':
                # 源码模式：保留完整 HTML 源码
                output_content = html_content
            else:
                # 文本提取模式：提取纯文本
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 移除脚本和样式
                for script in soup(['script', 'style']):
                    script.decompose()
                
                self.update_progress(input_path, 50)
                
                # 提取文本
                text = soup.get_text(separator='\n', strip=True)
                
                # 清理多余空行
                lines = [line.strip() for line in text.split('\n')]
                cleaned_lines = []
                prev_empty = False
                
                for line in lines:
                    is_empty = not line
                    if is_empty and prev_empty:
                        continue  # 跳过连续空行
                    cleaned_lines.append(line)
                    prev_empty = is_empty
                
                output_content = '\n'.join(cleaned_lines)
                
                self.update_progress(input_path, 80)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'mode': mode
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"HTML to TXT conversion failed: {str(e)}")
