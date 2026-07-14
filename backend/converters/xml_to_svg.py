import xml.etree.ElementTree as ET
import os
from .base import BaseConverter
from typing import Dict, Any


class XmlToSvgConverter(BaseConverter):
    """XML 到 SVG 转换器 - 支持SVG格式的XML文件"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['svg']
    
    def _is_svg_xml(self, root) -> bool:
        """检查XML是否是SVG格式"""
        # 检查根元素是否是svg
        tag = root.tag.lower()
        if '}' in tag:
            # 处理命名空间
            tag = tag.split('}')[1]
        
        return tag == 'svg'
    
    def _generate_svg_from_xml(self, root) -> str:
        """从普通XML生成简单的SVG可视化"""
        # 生成简单的树形结构SVG
        elements = []
        y_offset = 50
        
        def add_node(element, x, y, level=0):
            nonlocal y_offset
            
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            text = (element.text or '').strip()
            
            # 绘制节点
            node_text = f"{tag}"
            if text and len(text) < 30:
                node_text += f": {text}"
            
            # 节点矩形
            rect = f'<rect x="{x}" y="{y}" width="150" height="30" fill="#e3f2fd" stroke="#1976d2" stroke-width="1" rx="5"/>'
            elements.append(rect)
            
            # 节点文本
            text_elem = f'<text x="{x + 10}" y="{y + 20}" font-family="Arial" font-size="12" fill="#333">{node_text}</text>'
            elements.append(text_elem)
            
            current_y = y
            child_y = y + 50
            
            # 处理子元素
            for child in element:
                # 绘制连接线
                line = f'<line x1="{x + 75}" y1="{current_y + 30}" x2="{x + 75}" y2="{child_y}" stroke="#999" stroke-width="1"/>'
                elements.append(line)
                
                add_node(child, x + 20, child_y, level + 1)
                child_y += 50
            
            y_offset = max(y_offset, child_y)
        
        add_node(root, 50, 50)
        
        # 计算SVG尺寸
        width = 800
        height = max(y_offset + 50, 400)
        
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <rect width="100%" height="100%" fill="#ffffff"/>
    <g>
        <text x="20" y="30" font-family="Arial" font-size="16" font-weight="bold" fill="#333">XML Structure</text>
        {chr(10).join(elements)}
    </g>
</svg>'''
        
        return svg_content
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 XML 转换为 SVG"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 解析XML
            tree = ET.parse(input_path)
            root = tree.getroot()
            
            self.update_progress(input_path, 30)
            
            # 检查是否是SVG格式的XML
            if self._is_svg_xml(root):
                # 直接复制SVG内容
                with open(input_path, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                method = 'svg-xml-copy'
            else:
                # 生成XML结构的SVG可视化
                svg_content = self._generate_svg_from_xml(root)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                method = 'xml-structure-visualization'
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'method': method
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"XML to SVG conversion failed: {str(e)}")
