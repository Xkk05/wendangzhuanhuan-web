import shutil
from bs4 import BeautifulSoup
from .base import BaseConverter
from typing import Dict, Any


class HtmlToMarkdownConverter(BaseConverter):
    """HTML 到 Markdown 转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加进度回调
    2. 支持两种模式：源码模式 / 文本提取模式
    3. 基础的 HTML 到 Markdown 转换
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['md', 'markdown']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 HTML 转换为 Markdown"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 获取选项
            mode = options.get('mode', 'text')  # 'source' or 'text'
            
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            self.update_progress(input_path, 30)
            
            if mode == 'source':
                # 源码模式：直接复制 HTML 源码
                output_content = html_content
            else:
                # 文本提取模式：简单的 HTML 到 Markdown 转换
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 移除脚本和样式
                for script in soup(['script', 'style']):
                    script.decompose()
                
                self.update_progress(input_path, 50)
                
                # 基础转换
                md_lines = []
                
                # 标题
                for i in range(1, 7):
                    for heading in soup.find_all(f'h{i}'):
                        text = heading.get_text(strip=True)
                        if text:
                            md_lines.append(f"{'#' * i} {text}\n")
                        heading.decompose()
                
                # 段落
                for para in soup.find_all('p'):
                    text = para.get_text(strip=True)
                    if text:
                        md_lines.append(f"{text}\n")
                
                # 列表
                for ul in soup.find_all('ul'):
                    for li in ul.find_all('li'):
                        text = li.get_text(strip=True)
                        if text:
                            md_lines.append(f"- {text}\n")
                
                # 如果没有提取到内容，使用纯文本
                if not md_lines:
                    text = soup.get_text(separator='\n', strip=True)
                    output_content = text
                else:
                    output_content = '\n'.join(md_lines)
                
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
            raise Exception(f"HTML to Markdown conversion failed: {str(e)}")
