from .base import BaseConverter
from typing import Dict, Any
from backend.utils.html_content import prepare_content_soup, soup_text
from backend.utils.text_utils import read_text_file


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
            
            html_content = read_text_file(input_path, options.get('encoding'))
            
            self.update_progress(input_path, 30)
            
            if mode == 'source':
                # 源码模式：保留完整 HTML 源码
                output_content = html_content
            else:
                soup = prepare_content_soup(html_content, options)
                self.update_progress(input_path, 50)
                output_content = soup_text(soup)
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
