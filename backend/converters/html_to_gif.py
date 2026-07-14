import os
from .base import BaseConverter
from .html_to_image import HtmlToImageConverter
from typing import Dict, Any


class HtmlToGifConverter(BaseConverter):
    """HTML 到 GIF 转换器 - 通过PNG中间格式实现"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['gif']
        self.html_to_image = HtmlToImageConverter()
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 HTML 转换为 GIF（静态截图）"""
        temp_png_path = None
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 生成临时PNG文件
            base_dir = os.path.dirname(output_path) or os.getcwd()
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            temp_png_path = os.path.join(base_dir, base_name + "_temp.png")
            
            # 第一步：HTML -> PNG
            self.html_to_image.convert(input_path, temp_png_path, **options)
            self.update_progress(input_path, 50)
            
            # 第二步：PNG -> GIF
            try:
                from PIL import Image
                
                # 读取PNG并转换为GIF
                img = Image.open(temp_png_path)
                
                # 如果是RGBA模式，转换为RGB（GIF不支持透明度）
                if img.mode == 'RGBA':
                    # 创建白色背景
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])  # 使用alpha通道作为mask
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 保存为GIF
                img.save(output_path, 'GIF', optimize=True)
                
                self.update_progress(input_path, 100)
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'size': self.get_output_size(output_path),
                    'method': 'html->png->gif'
                }
                
            except ImportError:
                raise Exception("PIL/Pillow not installed. Install with: pip install Pillow")
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"HTML to GIF conversion failed: {str(e)}")
        finally:
            # 清理临时PNG文件
            if temp_png_path and os.path.exists(temp_png_path):
                try:
                    os.remove(temp_png_path)
                except:
                    pass
