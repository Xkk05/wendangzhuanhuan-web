import json
from bs4 import BeautifulSoup
from .base import BaseConverter
from typing import Dict, Any, List


class HtmlToJsonConverter(BaseConverter):
    """HTML 到 JSON 转换器 - 结构化提取HTML内容"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['json']
    
    def _extract_element(self, element, depth=0, max_depth=10) -> Dict[str, Any]:
        """递归提取HTML元素为字典结构"""
        if depth > max_depth:
            return None
        
        # 跳过注释和脚本
        if element.name in ['script', 'style', None]:
            return None
        
        result = {
            'tag': element.name,
        }
        
        # 提取属性
        if element.attrs:
            result['attributes'] = dict(element.attrs)
        
        # 提取文本内容（仅直接文本，不包括子元素）
        direct_text = ''.join([str(s) for s in element.contents if isinstance(s, str)]).strip()
        if direct_text:
            result['text'] = direct_text
        
        # 递归提取子元素
        children = []
        for child in element.children:
            if hasattr(child, 'name'):
                child_data = self._extract_element(child, depth + 1, max_depth)
                if child_data:
                    children.append(child_data)
        
        if children:
            result['children'] = children
        
        return result
    
    def _extract_metadata(self, soup) -> Dict[str, Any]:
        """提取HTML元数据"""
        metadata = {}
        
        # 提取标题
        title = soup.find('title')
        if title:
            metadata['title'] = title.get_text().strip()
        
        # 提取meta标签
        meta_tags = {}
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                meta_tags[name] = content
        
        if meta_tags:
            metadata['meta'] = meta_tags
        
        # 提取链接
        links = []
        for link in soup.find_all('a', href=True):
            links.append({
                'text': link.get_text().strip(),
                'href': link['href']
            })
        
        if links:
            metadata['links'] = links
        
        # 提取图片
        images = []
        for img in soup.find_all('img', src=True):
            images.append({
                'src': img['src'],
                'alt': img.get('alt', '')
            })
        
        if images:
            metadata['images'] = images
        
        return metadata
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 HTML 转换为 JSON"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 读取HTML文件
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            self.update_progress(input_path, 30)
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 获取选项
            mode = options.get('mode', 'structured')  # 'structured' or 'metadata'
            max_depth = options.get('max_depth', 10)
            
            self.update_progress(input_path, 50)
            
            if mode == 'metadata':
                # 仅提取元数据
                result = self._extract_metadata(soup)
            else:
                # 完整结构化提取
                body = soup.find('body')
                if body:
                    structure = self._extract_element(body, max_depth=max_depth)
                else:
                    structure = self._extract_element(soup, max_depth=max_depth)
                
                result = {
                    'metadata': self._extract_metadata(soup),
                    'structure': structure
                }
            
            self.update_progress(input_path, 80)
            
            # 写入JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'mode': mode
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"HTML to JSON conversion failed: {str(e)}")
