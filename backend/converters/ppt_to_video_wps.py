"""
PPT转视频转换器（使用WPS）

使用WPS Office的COM接口实现PPT转视频
"""

import os
import time
import shutil
import subprocess
import tempfile
import uuid
from typing import Dict, Any
from .base import BaseConverter


class PptToVideoWpsConverter(BaseConverter):
    """PPT转视频转换器（基于WPS）"""
    
    def __init__(self):
        super().__init__()
        self.ffmpeg_path = self._find_ffmpeg()
        
    def _find_ffmpeg(self) -> str:
        """查找FFmpeg"""
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            return ffmpeg
        common_paths = [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        return None
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """转换PPT为视频"""
        
        print(f"[WpsPptToVideo] 开始转换: {input_path}")
        self.validate_input(input_path)
        self.update_progress(input_path, 5)
        
        if not self.ffmpeg_path:
            raise Exception("FFmpeg未安装")
        
        try:
            import win32com.client
            import pythoncom
        except ImportError:
            raise Exception("pywin32未安装")
        
        temp_dir = tempfile.mkdtemp(prefix='wps_ppt_video_')
        
        try:
            # 步骤1：使用WPS将PPT导出为图片
            print(f"[WpsPptToVideo] 步骤1: 使用WPS导出图片...")
            self.update_progress(input_path, 20)
            
            image_files = self._ppt_to_images_wps(input_path, temp_dir)
            
            if not image_files:
                raise Exception("未能生成图片")
            
            print(f"[WpsPptToVideo] 生成了 {len(image_files)} 张图片")
            self.update_progress(input_path, 60)
            
            # 步骤2：使用FFmpeg合成视频
            print(f"[WpsPptToVideo] 步骤2: 合成视频...")
            
            slide_duration = options.get('slide_duration', 3)
            fps = options.get('fps', 24)
            resolution = options.get('resolution', 720)
            
            self._create_video(image_files, output_path, slide_duration, fps, resolution)
            
            self.update_progress(input_path, 100)
            print(f"[WpsPptToVideo] 转换完成: {output_path}")
            
            return {
                'success': True,
                'output_path': output_path,
                'size': os.path.getsize(output_path),
                'slides': len(image_files),
                'duration': len(image_files) * slide_duration
            }
            
        except Exception as e:
            raise Exception(f"WPS PPT转视频失败: {str(e)}")
            
        finally:
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    def _ppt_to_images_wps(self, ppt_path: str, output_dir: str) -> list:
        """使用WPS将PPT转为图片"""
        
        import win32com.client
        import pythoncom
        
        pythoncom.CoInitialize()
        wps_app = None
        presentation = None
        
        try:
            # 复制文件到临时位置
            temp_ppt = os.path.join(output_dir, f"temp_{uuid.uuid4().hex}.pptx")
            shutil.copy2(ppt_path, temp_ppt)
            print(f"[WpsPptToVideo] 临时文件: {temp_ppt}")
            
            # 尝试启动WPS演示（WPP）
            # WPS的COM接口名称可能是：
            # - WPP.Application (WPS演示)
            # - KWPP.Application (金山演示)
            
            wps_app = None
            for app_name in ['WPP.Application', 'KWPP.Application', 'Wps.Application']:
                try:
                    print(f"[WpsPptToVideo] 尝试启动: {app_name}")
                    wps_app = win32com.client.Dispatch(app_name)
                    print(f"[WpsPptToVideo] 成功启动: {app_name}")
                    break
                except Exception as e:
                    print(f"[WpsPptToVideo] {app_name} 启动失败: {e}")
                    continue
            
            if not wps_app:
                raise Exception("无法启动WPS演示。请确保已安装WPS Office")
            
            # 设置WPS属性 - 尝试隐藏窗口
            try:
                # WPS建议先可见再最小化
                wps_app.Visible = 1
                wps_app.WindowState = 2 # 最小化
                wps_app.DisplayAlerts = 0
            except Exception as e:
                print(f"[WpsPptToVideo] 无法设置WPS窗口状态: {e}")
            
            # 打开演示文稿
            abs_ppt_path = os.path.abspath(temp_ppt)
            print(f"[WpsPptToVideo] 打开文件 (Minimized): {abs_ppt_path}")
            
            # 优先使用 WithWindow=True 配合最小化，以确保 Export 可用
            try:
                presentation = wps_app.Presentations.Open(abs_ppt_path, ReadOnly=True, WithWindow=True)
            except Exception as e:
                print(f"[WpsPptToVideo] WPS Open WithWindow=True 失败: {e}，尝试无窗口模式...")
                try:
                    presentation = wps_app.Presentations.Open(abs_ppt_path, ReadOnly=True, WithWindow=False)
                except Exception as e2:
                    print(f"[WpsPptToVideo] WPS Open失败: {e2}")
                    raise e2
            time.sleep(2)
            
            slide_count = presentation.Slides.Count
            print(f"[WpsPptToVideo] 幻灯片数: {slide_count}")
            
            if slide_count == 0:
                raise Exception("PPT没有幻灯片")
            
            # 逐页导出为图片
            image_files = []
            abs_output_dir = os.path.abspath(output_dir)
            
            for i in range(1, slide_count + 1):
                slide = presentation.Slides(i)
                output_file = os.path.join(abs_output_dir, f"slide_{i:04d}.png")
                
                try:
                    # WPS的Export方法
                    slide.Export(output_file, "PNG", 1920, 1080)
                    
                    if os.path.exists(output_file):
                        image_files.append(output_file)
                        if i % 5 == 0 or i == slide_count:
                            print(f"[WpsPptToVideo] 已导出 {i}/{slide_count}")
                    else:
                        print(f"[WpsPptToVideo] 警告: 第{i}页导出失败")
                        
                except Exception as e:
                    print(f"[WpsPptToVideo] 导出第{i}页出错: {e}")
                    continue
            
            return image_files
            
        finally:
            if presentation:
                try:
                    presentation.Close()
                except:
                    pass
            if wps_app:
                try:
                    wps_app.Quit()
                except:
                    pass
            
            # 清理临时文件
            try:
                if 'temp_ppt' in locals() and os.path.exists(temp_ppt):
                    time.sleep(0.5)
                    os.remove(temp_ppt)
            except:
                pass
            
            pythoncom.CoUninitialize()
    
    def _ppt_to_images_wps(self, ppt_path: str, output_dir: str) -> list:
        """Prefer hidden WPS mode first, then fall back to minimized mode."""

        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()
        wps_app = None
        presentation = None

        try:
            temp_ppt = os.path.join(output_dir, f"temp_{uuid.uuid4().hex}.pptx")
            shutil.copy2(ppt_path, temp_ppt)

            for app_name in ['WPP.Application', 'KWPP.Application', 'Wps.Application']:
                try:
                    wps_app = win32com.client.Dispatch(app_name)
                    break
                except Exception:
                    continue

            if not wps_app:
                raise Exception("Unable to start WPS Presentation")

            hidden_mode = False
            try:
                wps_app.DisplayAlerts = 0
            except Exception as e:
                print(f"[WpsPptToVideo] Failed to disable WPS alerts: {e}")

            for visible_value in (0, False):
                try:
                    wps_app.Visible = visible_value
                    hidden_mode = True
                    break
                except Exception:
                    continue

            if not hidden_mode:
                try:
                    wps_app.Visible = 1
                    wps_app.WindowState = 2
                except Exception as e:
                    print(f"[WpsPptToVideo] Failed to minimize WPS: {e}")

            abs_ppt_path = os.path.abspath(temp_ppt)
            try:
                presentation = wps_app.Presentations.Open(abs_ppt_path, ReadOnly=True, WithWindow=not hidden_mode)
            except Exception as e:
                print(f"[WpsPptToVideo] Preferred WPS open mode failed: {e}")
                if hidden_mode:
                    try:
                        wps_app.Visible = 1
                        wps_app.WindowState = 2
                    except Exception:
                        pass
                presentation = wps_app.Presentations.Open(abs_ppt_path, ReadOnly=True, WithWindow=hidden_mode)

            time.sleep(1)

            slide_count = presentation.Slides.Count
            if slide_count == 0:
                raise Exception("PPT has no slides")

            image_files = []
            abs_output_dir = os.path.abspath(output_dir)
            for i in range(1, slide_count + 1):
                slide = presentation.Slides(i)
                output_file = os.path.join(abs_output_dir, f"slide_{i:04d}.png")

                try:
                    slide.Export(output_file, "PNG", 1920, 1080)
                except Exception as e:
                    print(f"[WpsPptToVideo] Export failed on slide {i}: {e}")
                    continue

                if os.path.exists(output_file):
                    image_files.append(output_file)

            return image_files

        finally:
            if presentation:
                try:
                    presentation.Close()
                except Exception:
                    pass
            if wps_app:
                try:
                    wps_app.Quit()
                except Exception:
                    pass
            try:
                if 'temp_ppt' in locals() and os.path.exists(temp_ppt):
                    time.sleep(0.5)
                    os.remove(temp_ppt)
            except Exception:
                pass
            pythoncom.CoUninitialize()

    def _create_video(self, image_files: list, output_path: str,
                     slide_duration: float, fps: int, resolution: int):
        """使用FFmpeg创建视频"""
        
        if not image_files:
            raise Exception("没有图片")
        
        list_file = os.path.join(os.path.dirname(image_files[0]), 'filelist.txt')
        
        with open(list_file, 'w', encoding='utf-8') as f:
            for img in image_files:
                img_path = os.path.abspath(img).replace('\\', '/')
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {slide_duration}\n")
            img_path = os.path.abspath(image_files[-1]).replace('\\', '/')
            f.write(f"file '{img_path}'\n")
        
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
        
        print(f"[WpsPptToVideo] 执行FFmpeg...")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg失败: {result.stderr}")
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("视频文件未生成")
        
        print(f"[WpsPptToVideo] 视频已创建")
