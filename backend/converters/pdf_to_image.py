import fitz
import os
import zipfile
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageStat
from .base import BaseConverter
from typing import Dict, Any, List

class PdfToImageConverter(BaseConverter):
    """PDF 到 图片转换器（优化版 - 支持文件夹输出和水印）
    
    优化内容：
    1. 支持多页输出为文件夹
    2. 支持背景颜色设置
    3. 支持水印添加
    4. 支持长图拼接
    5. 添加质量设置
    """
    
    # 质量预设
    QUALITY_SETTINGS = {
        'ultra': {'dpi': 300, 'quality': 100},
        'high': {'dpi': 200, 'quality': 95},
        'medium': {'dpi': 150, 'quality': 85}
    }
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['png', 'jpg', 'jpeg', 'bmp', 'tiff']
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 PDF 转换为图片（增强版）"""
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 5)
            
            # 获取选项
            target_ext = output_path.split('.')[-1].lower()
            if target_ext == 'jpeg': target_ext = 'jpg'
            
            quality = options.get('quality', 85)  # 1-100
            merge = options.get('merge', True)  # 默认合并为长图
            background_color = options.get('background_color', '#ffffff')
            auto_crop = options.get('auto_crop', True)  # 默认自动裁剪空白
            
            # 水印选项
            watermark_text = options.get('watermark_text', '')
            watermark_opacity = options.get('watermark_opacity', 30)
            watermark_size = options.get('watermark_size', 40)
            watermark_color = options.get('watermark_color', '#cccccc')
            watermark_angle = options.get('watermark_angle', 45)
            watermark_position = options.get('watermark_position', 'center')
            
            # DPI 设置
            if quality >= 90:
                dpi = 300
            elif quality >= 70:
                dpi = 200
            else:
                dpi = 150
            
            zoom = dpi / 72.0
            
            self.update_progress(input_path, 10)
            
            doc = fitz.open(input_path)
            page_count = doc.page_count
            
            if page_count == 0:
                doc.close()
                raise Exception("PDF file is empty")
            
            # 获取页码范围 (支持多种参数名)
            raw_page_range = options.get('pdf_page_range') or options.get('page_range')
            pages = self.parse_page_range(raw_page_range, total_pages=page_count)
            
            # 确定要处理的页面列表
            pages_to_process = pages if pages is not None else list(range(page_count))
            
            print(f"[PdfToImage] PDF 共 {page_count} 页, 将处理 {len(pages_to_process)} 页")
            self.update_progress(input_path, 15)
            
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            output_dir = os.path.dirname(output_path) or os.getcwd()
            
            mat = fitz.Matrix(zoom, zoom)
            images = []
            
            # 转换每一页
            for i, page_num in enumerate(pages_to_process):
                # 确保页码有效
                if page_num < 0 or page_num >= page_count:
                    continue
                    
                page = doc.load_page(page_num)
                
                if background_color and background_color.lower() != '#ffffff':
                    pix = page.get_pixmap(matrix=mat, alpha=True)
                    img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
                    if i == 0: # 只打印一次
                        print(f"[PdfToImage] 应用背景颜色: {background_color}")
                    img = self._apply_background_color(img, background_color)
                else:
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # 自动裁剪空白边距
                if auto_crop:
                    # 检查是否完全空白，如果是则跳过
                    if self._is_image_empty(img):
                        print(f"[PdfToImage] 第 {page_num + 1} 页为空白，已跳过")
                        continue
                    img = self._crop_to_content(img)
                
                images.append(img)
                
                # 更新进度 (15% ~ 60%)
                progress = 15 + int(((i + 1) / len(pages_to_process)) * 45)
                self.update_progress(input_path, progress)
            
            doc.close()
            self.update_progress(input_path, 65)
            
            # 应用水印
            if watermark_text:
                print(f"[PdfToImage] 应用水印: {watermark_text}")
                images = [self._apply_watermark(
                    img, watermark_text, watermark_opacity, 
                    watermark_size, watermark_color, watermark_angle, watermark_position
                ) for img in images]
            
            self.update_progress(input_path, 75)
            
            # 处理输出
            processed_count = len(images)
            if processed_count == 1:
                # 单页直接保存
                print(f"[PdfToImage] 保存单页图片")
                # 确保输出目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    
                self._save_image(images[0], output_path, target_ext, quality)
                self.update_progress(input_path, 100)
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'size': self.get_output_size(output_path),
                    'page_count': 1,
                    'merged': False
                }
            elif merge and processed_count > 1:
                # 合并为长图
                print(f"[PdfToImage] 合并 {processed_count} 页为长图")
                final_output = self._merge_to_long_image(
                    images, output_path, target_ext, quality
                )
                self.update_progress(input_path, 100)
                
                return {
                    'success': True,
                    'output_path': final_output,
                    'size': self.get_output_size(final_output),
                    'page_count': processed_count,
                    'merged': True
                }
            else:
                # 保存为文件夹
                print(f"[PdfToImage] 保存 {processed_count} 页到文件夹")
                final_output = self._save_to_folder(
                    images, output_path, target_ext, base_name, output_dir, quality, pages_to_process
                )
                self.update_progress(input_path, 100)
                
                return {
                    'success': True,
                    'output_path': final_output,
                    'size': self.get_output_size(final_output),
                    'page_count': processed_count,
                    'merged': False
                }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"PDF to Image conversion failed: {str(e)}")
    
    def _is_image_empty(self, img: Image.Image, threshold: int = 10) -> bool:
        """检查图片是否为空白（全背景色）"""
        try:
            if img.mode != 'RGB':
                temp_img = img.convert('RGB')
            else:
                temp_img = img
                
            bg_color = temp_img.getpixel((0, 0))
            bg = Image.new(temp_img.mode, temp_img.size, bg_color)
            diff = ImageChops.difference(temp_img, bg)
            diff_gray = diff.convert('L')
            
            # 如果最大差异小于阈值，认为是空白
            stat = ImageStat.Stat(diff_gray)
            return stat.max[0] < threshold
        except Exception:
            return False

    def _crop_to_content(self, img: Image.Image, padding: int = 20) -> Image.Image:
        """裁剪图片中的空白边距（增强版：带阈值处理）"""
        try:
            # 转换为 RGB 以便计算背景
            if img.mode != 'RGB':
                temp_img = img.convert('RGB')
            else:
                temp_img = img

            # 获取背景颜色（假设左上角第一个像素是背景）
            bg_color = temp_img.getpixel((0, 0))
            
            # 使用差异图和阈值来识别内容
            # 创建纯背景图
            bg = Image.new(temp_img.mode, temp_img.size, bg_color)
            
            # 计算差异
            diff = ImageChops.difference(temp_img, bg)
            
            # 转换为灰度图以简化阈值处理
            diff_gray = diff.convert('L')
            
            # 阈值处理：如果差异小于 10，则认为是背景（处理抗锯齿等微小差异）
            # point() 映射：小于 10 的变 0，大于等于 10 的变 255
            mask = diff_gray.point(lambda x: 0 if x < 10 else 255)
            
            # 获取内容边界框
            bbox = mask.getbbox()
            
            if bbox:
                print(f"[PdfToImage] 裁剪区域: {bbox}, 原图大小: {img.size}")
                # 加上一些内边距
                left, top, right, bottom = bbox
                left = max(0, left - padding)
                top = max(0, top - padding)
                right = min(img.width, right + padding)
                bottom = min(img.height, bottom + padding)
                
                return img.crop((left, top, right, bottom))
            else:
                print("[PdfToImage] 未检测到内容，跳过裁剪")
            return img
        except Exception as e:
            print(f"[PdfToImage] 裁剪失败: {e}")
            return img

    def _apply_background_color(self, img: Image.Image, color: str) -> Image.Image:
        try:
            if color.startswith('#'):
                color = color[1:]
            r_bg = int(color[0:2], 16)
            g_bg = int(color[2:4], 16)
            b_bg = int(color[4:6], 16)

            if (r_bg, g_bg, b_bg) == (255, 255, 255):
                if img.mode != 'RGB':
                    return img.convert('RGB')
                return img

            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            background = Image.new('RGB', img.size, (r_bg, g_bg, b_bg))
            alpha = img.split()[3]
            background.paste(img, mask=alpha)

            return background
        except Exception as e:
            print(f"[PdfToImage] 背景颜色应用失败: {e}")
            return img
    
    def _get_watermark_font(self, text: str, size: int):
        has_non_ascii = any(ord(ch) > 127 for ch in text)
        
        chinese_fonts = [
            "msyh.ttc",
            "msyh.ttf",
            "simhei.ttf",
            "simhei.ttc",
            "simfang.ttf",
            "simfang.ttc",
            "simkai.ttf",
            "simkai.ttc",
            "simsun.ttc",
        ]
        latin_fonts = ["arial.ttf"]
        
        if has_non_ascii:
            candidates = chinese_fonts + latin_fonts
        else:
            candidates = latin_fonts + chinese_fonts
        font_paths = []
        windows_dir = os.environ.get("WINDIR")
        if windows_dir:
            fonts_dir = os.path.join(windows_dir, "Fonts")
        else:
            fonts_dir = None
        
        for name in candidates:
            font_paths.append(name)
            if fonts_dir:
                font_paths.append(os.path.join(fonts_dir, name))
        
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        
        return ImageFont.load_default()
    
    def _apply_watermark(self, img: Image.Image, text: str, opacity: int, 
                        size: int, color: str, angle: int, position: str = "center") -> Image.Image:
        """应用水印"""
        try:
            # 创建水印层
            watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark)
            
            # 解析颜色
            if color.startswith('#'):
                color = color[1:]
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            alpha = int(255 * (opacity / 100))
            
            font = self._get_watermark_font(text, size)
            
            # 使用 textbbox 获取精确边界,并考虑可能为负的偏移量,防止文字被截断
            bbox = draw.textbbox((0, 0), text, font=font)
            x0, y0, x1, y1 = bbox
            text_width = x1 - x0
            text_height = y1 - y0
            
            text_img = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
            text_draw = ImageDraw.Draw(text_img)
            # 将绘制起点平移 -x0,-y0,保证完整包裹字形
            text_draw.text((-x0, -y0), text, fill=(r, g, b, alpha), font=font)
            
            if angle != 0:
                text_img = text_img.rotate(angle, expand=True)
            
            tw, th = text_img.size
            margin_x = max(10, int(img.width * 0.03))
            margin_y = max(10, int(img.height * 0.03))
            
            # 如果水印整体尺寸超过图片可用区域,按比例缩放以保证完整显示
            max_w = max(1, img.width - 2 * margin_x)
            max_h = max(1, img.height - 2 * margin_y)
            scale = min(max_w / tw, max_h / th, 1.0)
            if scale < 1.0:
                new_w = max(1, int(tw * scale))
                new_h = max(1, int(th * scale))
                text_img = text_img.resize((new_w, new_h), resample=Image.LANCZOS)
                tw, th = text_img.size
            
            pos = position or "center"
            pos = pos.lower()
            
            if pos.endswith("left"):
                x = margin_x
            elif pos.endswith("right"):
                x = img.width - tw - margin_x
            else:
                x = (img.width - tw) // 2
            
            if pos.startswith("top"):
                y = margin_y
            elif pos.startswith("bottom"):
                y = img.height - th - margin_y
            else:
                y = (img.height - th) // 2
            
            x = max(0, min(img.width - tw, x))
            y = max(0, min(img.height - th, y))
            
            watermark.paste(text_img, (x, y), text_img)
            
            img_with_watermark = img.convert('RGBA')
            img_with_watermark = Image.alpha_composite(img_with_watermark, watermark)
            return img_with_watermark.convert('RGB')
        except Exception as e:
            print(f"[PdfToImage] 水印应用失败: {e}")
            return img
    
    def _merge_to_long_image(self, images: List[Image.Image], output_path: str, 
                            target_ext: str, quality: int) -> str:
        """合并为长图"""
        # 垂直拼接
        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        
        merged = Image.new('RGB', (total_width, total_height), (255, 255, 255))
        
        y_offset = 0
        for img in images:
            merged.paste(img, (0, y_offset))
            y_offset += img.height
        
        # 保存
        self._save_image(merged, output_path, target_ext, quality)
        return output_path
    
    def _save_to_folder(self, images: List[Image.Image], output_path: str, 
                       target_ext: str, base_name: str, output_dir: str, quality: int, 
                       original_pages: List[int] = None) -> str:
        """保存到文件夹"""
        # 创建文件夹
        folder_path = os.path.join(output_dir, base_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 保存每张图片
        for idx, img in enumerate(images):
            if original_pages:
                # 使用原始页码命名 (original_pages 是 0-based, 输出为 1-based)
                page_num = original_pages[idx] + 1
                filename = os.path.join(folder_path, f"{page_num}.{target_ext}")
            else:
                # 默认命名
                filename = os.path.join(folder_path, f"{idx + 1}.{target_ext}")
                
            self._save_image(img, filename, target_ext, quality)
        
        # 打包为 ZIP
        zip_path = output_path.replace(f'.{target_ext}', '.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for idx in range(len(images)):
                if original_pages:
                    page_num = original_pages[idx] + 1
                    filename = os.path.join(folder_path, f"{page_num}.{target_ext}")
                    arcname = f"{base_name}/{page_num}.{target_ext}"
                else:
                    filename = os.path.join(folder_path, f"{idx + 1}.{target_ext}")
                    arcname = f"{base_name}/{idx + 1}.{target_ext}"
                    
                zf.write(filename, arcname)
        
        # 清理临时文件夹
        import shutil
        shutil.rmtree(folder_path)
        
        return zip_path
    
    def _save_image(self, img: Image.Image, path: str, target_ext: str, quality: int):
        """保存图片"""
        if target_ext in ['jpg', 'jpeg']:
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            img.save(path, 'JPEG', quality=quality, optimize=True)
        elif target_ext == 'png':
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(path, 'PNG', optimize=True)
        else:
            img.save(path, target_ext.upper())
