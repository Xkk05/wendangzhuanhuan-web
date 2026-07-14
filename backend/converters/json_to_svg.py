import json
import os
from .base import BaseConverter
from typing import Dict, Any


class JsonToSvgConverter(BaseConverter):
    """JSON 到 SVG 转换器 - 生成简单的树形可视化"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['svg']
    
    def _generate_tree_svg(self, data: Any, x: int = 50, y: int = 50, level: int = 0) -> tuple:
        """递归生成JSON树形结构的SVG元素"""
        elements = []
        node_height = 30
        node_spacing = 40
        level_spacing = 200
        
        if isinstance(data, dict):
            current_y = y
            for i, (key, value) in enumerate(data.items()):
                # 绘制键
                key_text = f'<text x="{x}" y="{current_y}" font-family="Arial" font-size="14" fill="#333">{key}:</text>'
                elements.append(key_text)
                
                # 如果值是简单类型，直接显示
                if isinstance(value, (str, int, float, bool, type(None))):
                    value_str = str(value)
                    if len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                    value_text = f'<text x="{x + 100}" y="{current_y}" font-family="Arial" font-size="14" fill="#0066cc">{value_str}</text>'
                    elements.append(value_text)
                    current_y += node_height
                else:
                    # 递归处理复杂类型
                    current_y += node_height
                    # 绘制连接线
                    line = f'<line x1="{x + 80}" y1="{current_y - node_height + 5}" x2="{x + level_spacing - 20}" y2="{current_y}" stroke="#999" stroke-width="1"/>'
                    elements.append(line)
                    
                    child_elements, child_height = self._generate_tree_svg(value, x + level_spacing, current_y, level + 1)
                    elements.extend(child_elements)
                    current_y = child_height
            
            return elements, current_y
            
        elif isinstance(data, list):
            current_y = y
            for i, item in enumerate(data):
                # 绘制数组索引
                index_text = f'<text x="{x}" y="{current_y}" font-family="Arial" font-size="14" fill="#666">[{i}]</text>'
                elements.append(index_text)
                
                if isinstance(item, (str, int, float, bool, type(None))):
                    value_str = str(item)
                    if len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                    value_text = f'<text x="{x + 50}" y="{current_y}" font-family="Arial" font-size="14" fill="#0066cc">{value_str}</text>'
                    elements.append(value_text)
                    current_y += node_height
                else:
                    current_y += node_height
                    line = f'<line x1="{x + 40}" y1="{current_y - node_height + 5}" x2="{x + level_spacing - 20}" y2="{current_y}" stroke="#999" stroke-width="1"/>'
                    elements.append(line)
                    
                    child_elements, child_height = self._generate_tree_svg(item, x + level_spacing, current_y, level + 1)
                    elements.extend(child_elements)
                    current_y = child_height
            
            return elements, current_y
        else:
            # 简单值
            value_str = str(data)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            text = f'<text x="{x}" y="{y}" font-family="Arial" font-size="14" fill="#0066cc">{value_str}</text>'
            return [text], y + node_height
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 JSON 转换为 SVG 树形图"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 读取JSON文件
            with open(input_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            self.update_progress(input_path, 30)
            
            # 生成SVG元素
            elements, max_height = self._generate_tree_svg(json_data)
            
            self.update_progress(input_path, 70)
            
            # 计算SVG尺寸
            width = 1200
            height = max(max_height + 50, 400)
            
            # 生成完整的SVG
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <rect width="100%" height="100%" fill="#ffffff"/>
    <g>
        <text x="20" y="30" font-family="Arial" font-size="18" font-weight="bold" fill="#333">JSON Structure</text>
        {chr(10).join(elements)}
    </g>
</svg>'''
            
            # 写入SVG文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'method': 'json-tree-visualization'
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"JSON to SVG conversion failed: {str(e)}")
