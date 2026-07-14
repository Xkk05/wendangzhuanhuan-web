"""
PPT转视频智能转换器

优先使用PowerPoint，如果没有则自动使用WPS
"""

import os
import time
import shutil
import subprocess
import tempfile
import uuid
from typing import Dict, Any
from .base import BaseConverter


class PptToVideoSmartConverter(BaseConverter):
    """PPT转视频智能转换器（自动选择PowerPoint或WPS）"""
    
    def __init__(self):
        super().__init__()
        self.ffmpeg_path = self._find_ffmpeg()
        self.office_type = self._detect_office()
        
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
    
    def _detect_office(self) -> str:
        """检测可用的Office软件"""
        try:
            import win32com.client
            import pythoncom
            
            pythoncom.CoInitialize()
            
            # 1. 优先尝试PowerPoint
            try:
                ppt_app = win32com.client.Dispatch("PowerPoint.Application")
                version = ppt_app.Version
                ppt_app.Quit()
                pythoncom.CoUninitialize()
                print(f"[SmartPptToVideo] 检测到 Microsoft PowerPoint {version}")
                return "PowerPoint"
            except:
                pass
            
            # 2. 尝试WPS
            for app_name in ['WPP.Application', 'KWPP.Application']:
                try:
                    wps_app = win32com.client.Dispatch(app_name)
                    wps_app.Quit()
                    pythoncom.CoUninitialize()
                    print(f"[SmartPptToVideo] 检测到 WPS Office ({app_name})")
                    return app_name
                except:
                    continue
            
            pythoncom.CoUninitialize()
            
        except ImportError:
            pass
        
        return None
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """转换PPT为视频"""
        
        print(f"[SmartPptToVideo] 开始转换: {input_path}")
        print(f"[SmartPptToVideo] 初始检测: {self.office_type or '未检测到Office软件'}")
        
        self.validate_input(input_path)
        self.update_progress(input_path, 5)
        
        if not self.ffmpeg_path:
            raise Exception("FFmpeg未安装。请安装FFmpeg")
        
        if not self.office_type:
            raise Exception("未检测到PowerPoint或WPS。请安装其中之一")
        
        try:
            import win32com.client
            import pythoncom
        except ImportError:
            raise Exception("pywin32未安装")
        
        temp_dir = tempfile.mkdtemp(prefix='ppt_video_')
        
        try:
            # 步骤1：导出图片
            print(f"[SmartPptToVideo] 步骤1: 导出图片...")
            self.update_progress(input_path, 20)
            
            image_files = None
            last_error = None
            
            # 尝试使用检测到的Office软件
            try:
                if self.office_type == "PowerPoint":
                    print(f"[SmartPptToVideo] 尝试使用 PowerPoint...")
                    image_files = self._ppt_to_images_powerpoint(input_path, temp_dir)
                else:
                    print(f"[SmartPptToVideo] 尝试使用 WPS...")
                    image_files = self._ppt_to_images_wps(input_path, temp_dir)
            except Exception as e:
                last_error = e
                print(f"[SmartPptToVideo] {self.office_type} 失败: {e}")
                
                # 如果PowerPoint失败，尝试WPS
                if self.office_type == "PowerPoint":
                    print(f"[SmartPptToVideo] 回退到 WPS...")
                    try:
                        # 重新检测WPS
                        for app_name in ['KWPP.Application', 'WPP.Application']:
                            try:
                                pythoncom.CoInitialize()
                                test_app = win32com.client.Dispatch(app_name)
                                test_app.Quit()
                                pythoncom.CoUninitialize()
                                self.office_type = app_name
                                print(f"[SmartPptToVideo] 找到 WPS: {app_name}")
                                break
                            except:
                                continue
                        
                        if self.office_type in ['KWPP.Application', 'WPP.Application']:
                            image_files = self._ppt_to_images_wps(input_path, temp_dir)
                    except Exception as e2:
                        print(f"[SmartPptToVideo] WPS 也失败: {e2}")
                        raise Exception(f"PowerPoint和WPS都无法转换: PowerPoint错误={last_error}, WPS错误={e2}")
            
            if not image_files:
                raise Exception(f"未能生成图片。最后错误: {last_error}")
            
            print(f"[SmartPptToVideo] 生成了 {len(image_files)} 张图片")
            self.update_progress(input_path, 60)
            
            # 步骤2：合成视频
            print(f"[SmartPptToVideo] 步骤2: 合成视频...")
            
            slide_duration = options.get('slide_duration', 3)
            fps = options.get('fps', 24)
            resolution = options.get('resolution', 720)
            
            self._create_video(image_files, output_path, slide_duration, fps, resolution)
            
            self.update_progress(input_path, 100)
            print(f"[SmartPptToVideo] 转换完成: {output_path}")
            
            return {
                'success': True,
                'output_path': output_path,
                'size': os.path.getsize(output_path),
                'slides': len(image_files),
                'duration': len(image_files) * slide_duration,
                'converter': self.office_type
            }
            
        except Exception as e:
            raise Exception(f"PPT转视频失败: {str(e)}")
            
        finally:
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    def _kill_process(self, process_name: str):
        """强制结束进程"""
        try:
            os.system(f"taskkill /f /im {process_name} >nul 2>&1")
        except:
            pass

    def _ppt_to_images_powerpoint(self, ppt_path: str, output_dir: str) -> list:
        """使用PowerPoint导出图片"""
        
        import win32com.client
        import pythoncom
        
        # 转换前尝试清理残留进程
        self._kill_process("POWERPNT.EXE")
        
        pythoncom.CoInitialize()
        ppt_app = None
        presentation = None
        
        try:
            # 使用绝对路径
            abs_path = os.path.abspath(ppt_path)
            if not os.path.exists(abs_path):
                raise Exception(f"文件不存在: {abs_path}")
            
            print(f"[SmartPptToVideo] 文件路径: {abs_path}")
            
            # 启动PowerPoint
            try:
                ppt_app = win32com.client.Dispatch("PowerPoint.Application")
            except Exception as e:
                print(f"[SmartPptToVideo] Dispatch PowerPoint.Application 失败: {e}")
                # 尝试强制重启
                self._kill_process("POWERPNT.EXE")
                time.sleep(1)
                ppt_app = win32com.client.Dispatch("PowerPoint.Application")
            
            # 尝试隐藏PowerPoint窗口
            try:
                # 注意：有些版本必须先 Visible = 1 才能设置 WindowState
                ppt_app.Visible = 1 
                ppt_app.WindowState = 2 # 最小化
                ppt_app.DisplayAlerts = 0
            except Exception as e:
                print(f"[SmartPptToVideo] 设置窗口状态失败: {e}")
            
            # 尝试打开文件
            try:
                # 对于旧版 PowerPoint (如 2007/12.0)，WithWindow=False 可能导致 Export 失败
                # 因此我们优先使用 WithWindow=True，配合之前的 WindowState=2 (最小化) 来实现隐藏
                print(f"[SmartPptToVideo] 尝试打开文件 (Minimized): {abs_path}")
                presentation = ppt_app.Presentations.Open(abs_path, ReadOnly=True, WithWindow=True)
            except Exception as e:
                print(f"[SmartPptToVideo] Open WithWindow=True 失败: {e}，尝试无窗口模式...")
                try:
                    presentation = ppt_app.Presentations.Open(abs_path, ReadOnly=True, WithWindow=False)
                except Exception as e2:
                    print(f"[SmartPptToVideo] Open完全失败: {e2}")
                    raise e2
            
            time.sleep(1)
            
            slide_count = presentation.Slides.Count
            print(f"[SmartPptToVideo] PowerPoint: {slide_count} 页")
            
            # 导出图片
            image_files = []
            for i in range(1, slide_count + 1):
                slide = presentation.Slides(i)
                output_file = os.path.join(output_dir, f"slide_{i:04d}.png")
                
                try:
                    slide.Export(output_file, "PNG", 1920, 1080)
                except:
                    # 如果带参数失败，尝试不带参数
                    slide.Export(output_file, "PNG")
                
                if os.path.exists(output_file):
                    image_files.append(output_file)
                    if i % 5 == 0 or i == slide_count:
                        print(f"[SmartPptToVideo] 已导出 {i}/{slide_count}")
            
            return image_files
            
        finally:
            if presentation:
                try:
                    presentation.Close()
                except:
                    pass
            if ppt_app:
                try:
                    ppt_app.Quit()
                except:
                    pass
            pythoncom.CoUninitialize()
    
    def _ppt_to_images_wps(self, ppt_path: str, output_dir: str) -> list:
        """使用WPS导出图片"""
        
        import win32com.client
        import pythoncom
        
        # 转换前尝试清理残留进程
        self._kill_process("wps.exe")
        
        pythoncom.CoInitialize()
        wps_app = None
        presentation = None
        
        try:
            # 使用绝对路径
            abs_path = os.path.abspath(ppt_path)
            if not os.path.exists(abs_path):
                raise Exception(f"文件不存在: {abs_path}")
                
            print(f"[SmartPptToVideo] 文件路径: {abs_path}")
            
            # 启动WPS
            try:
                wps_app = win32com.client.Dispatch(self.office_type)
            except Exception as e:
                print(f"[SmartPptToVideo] Dispatch WPS 失败: {e}")
                self._kill_process("wps.exe")
                time.sleep(1)
                wps_app = win32com.client.Dispatch(self.office_type)
            
            # 尝试隐藏WPS窗口
            try:
                # WPS 建议先 Visible=True 再最小化，或者直接尝试 Visible=False
                # 如果是 RPC 服务器不可用，通常是因为 Visible=0 导致崩溃
                wps_app.Visible = 1
                wps_app.WindowState = 2 # 最小化
                wps_app.DisplayAlerts = 0
            except Exception as e:
                print(f"[SmartPptToVideo] 无法设置WPS窗口状态: {e}")
            
            # 尝试打开文件
            try:
                print(f"[SmartPptToVideo] WPS尝试打开 (Minimized): {abs_path}")
                # WPS 同样优先使用 WithWindow=True 配合最小化，以确保 Export 可用
                presentation = wps_app.Presentations.Open(abs_path, ReadOnly=True, WithWindow=True)
            except Exception as e:
                print(f"[SmartPptToVideo] WPS Open WithWindow=True 失败: {e}，尝试无窗口模式...")
                try:
                    presentation = wps_app.Presentations.Open(abs_path, ReadOnly=True, WithWindow=False)
                except Exception as e2:
                    print(f"[SmartPptToVideo] WPS Open完全失败: {e2}")
                    raise e2
            
            time.sleep(1)
            
            slide_count = presentation.Slides.Count
            print(f"[SmartPptToVideo] WPS: {slide_count} 页")
            
            # 导出图片
            image_files = []
            for i in range(1, slide_count + 1):
                slide = presentation.Slides(i)
                output_file = os.path.join(output_dir, f"slide_{i:04d}.png")
                
                try:
                    slide.Export(output_file, "PNG", 1920, 1080)
                except:
                    try:
                        # 如果带参数失败，尝试不带参数
                        slide.Export(output_file, "PNG")
                    except Exception as e:
                        print(f"[SmartPptToVideo] 第{i}页导出失败: {e}")
                        continue
                
                if os.path.exists(output_file):
                    image_files.append(output_file)
                    if i % 5 == 0 or i == slide_count:
                        print(f"[SmartPptToVideo] 已导出 {i}/{slide_count}")
            
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
            pythoncom.CoUninitialize()
    
    def _ppt_to_images_wps(self, ppt_path: str, output_dir: str) -> list:
        """Prefer hidden WPS mode first, then fall back to minimized mode."""

        import win32com.client
        import pythoncom

        self._kill_process("wps.exe")

        pythoncom.CoInitialize()
        wps_app = None
        presentation = None

        try:
            abs_path = os.path.abspath(ppt_path)
            if not os.path.exists(abs_path):
                raise Exception(f"File not found: {abs_path}")

            try:
                wps_app = win32com.client.Dispatch(self.office_type)
            except Exception:
                self._kill_process("wps.exe")
                time.sleep(1)
                wps_app = win32com.client.Dispatch(self.office_type)

            hidden_mode = False
            try:
                wps_app.DisplayAlerts = 0
            except Exception as e:
                print(f"[SmartPptToVideo] Failed to disable WPS alerts: {e}")

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
                    print(f"[SmartPptToVideo] Failed to minimize WPS: {e}")

            try:
                presentation = wps_app.Presentations.Open(abs_path, ReadOnly=True, WithWindow=not hidden_mode)
            except Exception as e:
                print(f"[SmartPptToVideo] Preferred WPS open mode failed: {e}")
                if hidden_mode:
                    try:
                        wps_app.Visible = 1
                        wps_app.WindowState = 2
                    except Exception:
                        pass
                presentation = wps_app.Presentations.Open(abs_path, ReadOnly=True, WithWindow=hidden_mode)

            time.sleep(1)

            slide_count = presentation.Slides.Count
            image_files = []
            for i in range(1, slide_count + 1):
                slide = presentation.Slides(i)
                output_file = os.path.join(output_dir, f"slide_{i:04d}.png")
                try:
                    slide.Export(output_file, "PNG", 1920, 1080)
                except Exception:
                    try:
                        slide.Export(output_file, "PNG")
                    except Exception as e:
                        print(f"[SmartPptToVideo] Export failed on slide {i}: {e}")
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
        
        print(f"[SmartPptToVideo] 执行FFmpeg...")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg失败: {result.stderr}")
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("视频文件未生成")
        
        print(f"[SmartPptToVideo] 视频已创建")
