"""
PPT转视频通用转换器（轻量级方案）

方案：直接用Python库将PPT渲染为图片，然后用FFmpeg合成视频
不需要PowerPoint、WPS或LibreOffice
"""

import os
import shutil
import subprocess
import tempfile
from typing import Dict, Any
from pathlib import Path
from .base import BaseConverter


class PptToVideoUniversalConverter(BaseConverter):
    """PPT转视频通用转换器（轻量级）"""
    
    def __init__(self):
        super().__init__()
        self.ffmpeg_path = self._find_ffmpeg()
        
    def _find_ffmpeg(self) -> str:
        """查找FFmpeg"""
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            return ffmpeg
            
        # Windows常见路径
        common_paths = [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
                
        return None
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """
        转换PPT为视频
        
        Args:
            input_path: PPT文件路径
            output_path: 输出视频路径
            **options: 转换选项
                - slide_duration: 每页持续时间（秒），默认3
                - fps: 帧率，默认24
                - resolution: 分辨率高度，默认720
        """
        print(f"[UniversalPptToVideo] 开始转换: {input_path}")
        
        self.validate_input(input_path)
        self.update_progress(input_path, 5)
        
        # 检查FFmpeg
        if not self.ffmpeg_path:
            raise Exception("FFmpeg未安装。请安装FFmpeg或使用在线安装：choco install ffmpeg")
        
        print(f"[UniversalPptToVideo] FFmpeg: {self.ffmpeg_path}")
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix='ppt_video_')
        
        try:
            # 步骤1：PPT转图片（使用aspose.slides）
            print(f"[UniversalPptToVideo] 步骤1: 转换PPT为图片...")
            self.update_progress(input_path, 20)
            image_files = self._ppt_to_images_aspose(input_path, temp_dir)
            
            if not image_files:
                raise Exception("未能生成图片")
            
            print(f"[UniversalPptToVideo] 生成了 {len(image_files)} 张图片")
            self.update_progress(input_path, 60)
            
            # 步骤2：图片合成视频
            print(f"[UniversalPptToVideo] 步骤2: 合成视频...")
            
            slide_duration = options.get('slide_duration', 3)
            fps = options.get('fps', 24)
            resolution = options.get('resolution', 720)
            
            self._create_video(image_files, output_path, slide_duration, fps, resolution)
            
            self.update_progress(input_path, 100)
            
            print(f"[UniversalPptToVideo] 转换完成: {output_path}")
            
            return {
                'success': True,
                'output_path': output_path,
                'size': os.path.getsize(output_path),
                'slides': len(image_files),
                'duration': len(image_files) * slide_duration
            }
            
        except Exception as e:
            raise Exception(f"PPT转视频失败: {str(e)}")
            
        finally:
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    def _ppt_to_images_aspose(self, ppt_path: str, output_dir: str) -> list:
        """使用aspose.slides将PPT转为图片（免费试用版）"""
        
        try:
            import aspose.slides as slides
        except ImportError:
            raise Exception("aspose.slides未安装。请运行: pip install aspose.slides")
        
        print(f"[UniversalPptToVideo] 加载PPT文件...")
        
        # 加载演示文稿
        presentation = slides.Presentation(ppt_path)
        
        slide_count = len(presentation.slides)
        print(f"[UniversalPptToVideo] PPT有 {slide_count} 页")
        
        image_files = []
        
        # 逐页导出为图片
        for i, slide in enumerate(presentation.slides, 1):
            image_path = os.path.join(output_dir, f'slide_{i:04d}.png')
            
            # 导出为图片（默认分辨率）
            slide.get_thumbnail(2.0, 2.0).save(image_path, slides.ImageFormat.PNG)
            
            image_files.append(image_path)
            
            if i % 5 == 0 or i == slide_count:
                print(f"[UniversalPptToVideo] 已导出 {i}/{slide_count} 页")
        
        presentation.dispose()
        
        return image_files
    
    def _create_video(self, image_files: list, output_path: str, 
                     slide_duration: float, fps: int, resolution: int):
        """使用FFmpeg创建视频"""
        
        if not image_files:
            raise Exception("没有图片可以创建视频")
        
        # 创建文件列表
        list_file = os.path.join(os.path.dirname(image_files[0]), 'filelist.txt')
        
        with open(list_file, 'w', encoding='utf-8') as f:
            for img in image_files:
                img_path = os.path.abspath(img).replace('\\', '/')
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {slide_duration}\n")
            # 最后一张图片需要再写一次
            img_path = os.path.abspath(image_files[-1]).replace('\\', '/')
            f.write(f"file '{img_path}'\n")
        
        # FFmpeg命令
        cmd = [
            self.ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-vf', f'scale=-2:{resolution}',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-r', str(fps),
            '-y',
            output_path
        ]
        
        print(f"[UniversalPptToVideo] 执行FFmpeg...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg失败: {result.stderr}")
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("视频文件未生成或为空")
        
        print(f"[UniversalPptToVideo] 视频已创建: {output_path}")

