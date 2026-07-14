import os
import logging
from .base import BaseConverter
from typing import Dict, Any
from html2image import Html2Image
from PIL import Image
import base64

logger = logging.getLogger(__name__)


class HtmlToSvgConverter(BaseConverter):
    """HTML 到 SVG 转换器
    
    实现策略：
    1. 主策略：通过浏览器截图转PNG，然后嵌入SVG
    2. 优化：保留矢量元素（如果HTML中包含SVG）
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['svg']
        self.hti = None
        self._init_browser()
    
    def _init_browser(self):
        """初始化浏览器"""
        try:
            # Windows: 优先使用 Edge
            edge_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ]
            
            for edge_path in edge_paths:
                if os.path.exists(edge_path):
                    logger.info(f"Using Edge browser at {edge_path}")
                    self.hti = Html2Image(browser_executable=edge_path)
                    return
            
            # 尝试 Chrome
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    logger.info(f"Using Chrome browser at {chrome_path}")
                    self.hti = Html2Image(browser_executable=chrome_path)
                    return
            
            # 使用默认
            logger.warning("No browser found, using default")
            self.hti = Html2Image()
            
        except Exception as e:
            logger.error(f"Failed to initialize Html2Image: {e}")
            self.hti = None
    
    def _extract_svg_from_html(self, html_content: str) -> str:
        """尝试从HTML中提取SVG元素"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            svg_tags = soup.find_all('svg')
            
            if svg_tags and len(svg_tags) == 1:
                # 如果只有一个SVG标签，直接返回
                svg_content = str(svg_tags[0])
                # 确保有xmlns属性
                if 'xmlns' not in svg_content:
                    svg_content = svg_content.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"', 1)
                return svg_content
            
        except Exception as e:
            logger.warning(f"Failed to extract SVG from HTML: {e}")
        
        return None
    
    def _convert_via_screenshot(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """通过截图方式转换：HTML -> PNG -> SVG（嵌入图片）"""
        if not self.hti:
            raise Exception("浏览器初始化失败，无法进行截图转换")
        
        # 读取 HTML 内容
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        self.update_progress(input_path, 20)
        
        # 注入白色背景
        bg_css = '''<style>
            html, body { 
                background-color: #ffffff !important; 
                margin: 0;
                padding: 20px;
            }
        </style>'''
        
        if '<head>' in html_content:
            html_content = html_content.replace('<head>', f'<head>{bg_css}')
        elif '<html>' in html_content:
            html_content = html_content.replace('<html>', f'<html><head>{bg_css}</head>')
        else:
            html_content = f'<html><head>{bg_css}</head><body>{html_content}</body></html>'
        
        # 配置参数
        width = options.get('width', 1280)
        height = options.get('height', 800)
        
        self.update_progress(input_path, 30)
        
        # 设置输出目录
        output_dir = os.path.dirname(output_path) or os.getcwd()
        self.hti.output_path = output_dir
        
        # 截图为 PNG
        temp_filename = os.path.basename(output_path) + '_temp.png'
        
        self.hti.screenshot(
            html_str=html_content,
            save_as=temp_filename,
            size=(width, height)
        )
        
        temp_path = os.path.join(output_dir, temp_filename)
        
        if not os.path.exists(temp_path):
            raise Exception("截图失败，未生成图片文件")
        
        self.update_progress(input_path, 60)
        
        # 读取PNG并转换为base64
        with open(temp_path, 'rb') as img_file:
            img_data = img_file.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
        
        # 获取图片尺寸
        img = Image.open(temp_path)
        img_width, img_height = img.size
        img.close()
        
        self.update_progress(input_path, 80)
        
        # 创建SVG，嵌入PNG图片
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{img_width}" 
     height="{img_height}" 
     viewBox="0 0 {img_width} {img_height}">
    <title>HTML to SVG Conversion</title>
    <image x="0" y="0" width="{img_width}" height="{img_height}" 
           xlink:href="data:image/png;base64,{img_base64}" />
</svg>'''
        
        # 保存SVG文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        # 清理临时文件
        try:
            os.remove(temp_path)
        except:
            pass
        
        self.update_progress(input_path, 100)
        
        return {
            'success': True,
            'output_path': output_path,
            'size': self.get_output_size(output_path),
            'width': img_width,
            'height': img_height,
            'method': 'screenshot_embedded'
        }
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 HTML 转换为 SVG"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 5)
            
            # 读取HTML内容
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            self.update_progress(input_path, 10)
            
            # 策略1: 如果HTML中只包含一个SVG元素，直接提取
            svg_content = self._extract_svg_from_html(html_content)
            
            if svg_content:
                # 直接保存提取的SVG
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                self.update_progress(input_path, 100)
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'size': self.get_output_size(output_path),
                    'method': 'svg_extracted'
                }
            
            # 策略2: 通过截图方式转换
            return self._convert_via_screenshot(input_path, output_path, **options)
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"HTML to SVG conversion failed: {str(e)}")
