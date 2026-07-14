import os
from PIL import Image, ImageDraw, ImageFont
from .base import BaseConverter
from typing import Dict, Any


class TxtToImageConverter(BaseConverter):
    """TXT 到 图片转换器（优化版 - 参考 conversion_core）
    
    优化内容：
    1. 添加进度回调
    2. 更好的字体加载策略
    3. 可配置样式（字体、颜色、间距）
    4. 自动换行优化
    """
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['png', 'jpg', 'jpeg']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 TXT 转换为图片（增强版）"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            self.update_progress(input_path, 20)
            
            # 配置参数
            font_size = options.get('font_size', 16)
            padding = options.get('padding', 40)
            bg_color = options.get('bg_color') or options.get('background_color', '#ffffff')
            text_color = options.get('text_color', '#000000')
            max_width = options.get('max_width', 800)
            line_spacing = options.get('line_spacing', 8)
            
            # 尝试加载中文字体
            font = None
            font_paths = [
                r"C:\Windows\Fonts\msyh.ttc",
                r"C:\Windows\Fonts\simsun.ttc",
                r"C:\Windows\Fonts\simhei.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        break
                    except:
                        continue
            
            if font is None:
                font = ImageFont.load_default()
            
            self.update_progress(input_path, 30)
            
            # 创建临时图片计算文本尺寸
            temp_img = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(temp_img)
            
            # 自动换行处理
            lines = []
            for paragraph in text.split('\n'):
                if not paragraph:
                    lines.append('')
                    continue
                
                words = list(paragraph)
                current_line = ''
                for char in words:
                    test_line = current_line + char
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    if bbox[2] - bbox[0] <= max_width - padding * 2:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = char
                if current_line:
                    lines.append(current_line)
            
            self.update_progress(input_path, 50)
            
            # 计算图片尺寸
            line_height = font_size + line_spacing
            img_width = max_width
            img_height = padding * 2 + len(lines) * line_height
            
            # 限制最大高度（防止过大）
            max_height = 10000
            if img_height > max_height:
                img_height = max_height
                print(f"[Warning] Image height limited to {max_height}px")
            
            # 创建最终图片
            img = Image.new('RGB', (img_width, img_height), bg_color)
            draw = ImageDraw.Draw(img)
            
            self.update_progress(input_path, 60)
            
            # 绘制文本
            y = padding
            for idx, line in enumerate(lines):
                if y + line_height > img_height - padding:
                    break  # 超出图片高度，停止绘制
                draw.text((padding, y), line, font=font, fill=text_color)
                y += line_height
                
                # 更新进度 (60% ~ 90%)
                if idx % 10 == 0:
                    progress = 60 + int((idx / len(lines)) * 30)
                    self.update_progress(input_path, progress)
            
            self.update_progress(input_path, 90)
            
            # 保存图片
            target_ext = output_path.split('.')[-1].lower()
            if target_ext in ['jpg', 'jpeg']:
                img = img.convert('RGB')
                img.save(output_path, 'JPEG', quality=95)
            else:
                img.save(output_path, 'PNG')
            
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': self.get_output_size(output_path),
                'line_count': len(lines),
                'dimensions': f'{img_width}x{img_height}'
            }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"TXT to Image conversion failed: {str(e)}")
