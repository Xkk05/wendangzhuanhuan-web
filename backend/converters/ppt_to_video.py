import os
import time
import logging
import sys
from typing import Dict, Any
from .base import BaseConverter
import platform
from datetime import datetime
import tempfile
from backend.utils.logger import setup_logger

class PptToVideoConverter(BaseConverter):
    """PPT 转视频转换器 (仅限 Windows, 需要安装 PowerPoint)"""
    
    def __init__(self):
        super().__init__()
        # 初始化日志
        self.logger = setup_logger('PptToVideo')
            
    def _log(self, level, message):
        """记录日志"""
        if self.logger:
            if level == 'info':
                self.logger.info(message)
            elif level == 'error':
                self.logger.error(message)
            elif level == 'warning':
                self.logger.warning(message)
            elif level == 'debug':
                self.logger.debug(message)
        else:
            print(f"[PptToVideo] {message}")
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        self._log('info', "="*60)
        self._log('info', "开始PPT转视频转换")
        self._log('info', f"输入文件: {input_path}")
        self._log('info', f"输出文件: {output_path}")
        self._log('info', f"转换选项: {options}")
        self._log('info', "="*60)
        
        self.validate_input(input_path)
        self.update_progress(input_path, 5)
        
        if platform.system() != 'Windows':
            self._log('error', "不支持的操作系统")
            raise Exception("PPT to Video conversion is only supported on Windows")
            
        try:
            import win32com.client
            import pythoncom
            self._log('info', "成功导入win32com库")
        except ImportError as e:
            self._log('error', f"导入pywin32失败: {e}")
            raise Exception("pywin32 library not found. Please install it.")
            
        # 创建临时工作目录
        import tempfile
        import shutil
        import uuid
        
        # 1. 复制输入文件到纯 ASCII 路径的临时文件
        temp_dir = tempfile.gettempdir()
        original_ext = os.path.splitext(input_path)[1]
        temp_input_name = f"ppt_temp_{uuid.uuid4().hex}{original_ext}"
        temp_input_path = os.path.join(temp_dir, temp_input_name)
        
        self._log('info', f"原始文件: {input_path}")
        self._log('info', f"原始文件名: {os.path.basename(input_path)}")
        self._log('info', f"文件扩展名: {original_ext}")
        
        try:
            shutil.copy2(input_path, temp_input_path)
            self._log('info', f"成功复制到临时文件: {temp_input_path}")
            self._log('info', f"临时文件大小: {os.path.getsize(temp_input_path)} bytes")
            working_input_path = temp_input_path
        except Exception as e:
            self._log('warning', f"复制失败: {e}，使用原始路径")
            working_input_path = input_path

        ppt_app = None
        presentation = None
        
        try:
            # 初始化 COM
            self._log('info', "初始化COM...")
            pythoncom.CoInitialize()
            
            # 解锁文件
            try:
                import subprocess
                self._log('info', f"解锁文件: {working_input_path}")
                subprocess.run(
                    ["powershell", "Unblock-File", "-Path", f"'{working_input_path}'"], 
                    check=True, capture_output=True, timeout=10
                )
                self._log('info', "文件解锁成功")
            except Exception as e:
                self._log('warning', f"文件解锁失败: {e}")

            # 启动 PowerPoint
            try:
                self._log('info', "启动PowerPoint...")
                ppt_app = win32com.client.Dispatch("PowerPoint.Application")
                version = ppt_app.Version
                self._log('info', f"PowerPoint版本: {version}")
                
                # 尝试隐藏窗口
                try:
                    ppt_app.Visible = 1
                    ppt_app.WindowState = 2 # 最小化
                    ppt_app.DisplayAlerts = 0
                except Exception as e:
                    self._log('warning', f"无法设置窗口状态: {e}")
            except Exception as e:
                self._log('error', f"PowerPoint启动失败: {e}")
                self._log('info', "清理残留进程...")
                os.system("taskkill /F /IM POWERPNT.EXE")
                time.sleep(2)
                ppt_app = win32com.client.Dispatch("PowerPoint.Application")
                
                # 尝试隐藏窗口
                try:
                    ppt_app.Visible = 1
                    ppt_app.WindowState = 2 # 最小化
                    ppt_app.DisplayAlerts = 0
                except Exception as e:
                    self._log('warning', f"无法设置窗口状态: {e}")
                self._log('info', "PowerPoint重启成功")
            
            self.update_progress(input_path, 20)
            
            # 打开演示文稿
            try:
                self._log('info', f"打开演示文稿 (Minimized): {working_input_path}")
                # 对于旧版 PowerPoint (如 2007/12.0)，WithWindow=False 可能导致转换失败
                # 因此我们优先使用 WithWindow=True，配合之前的 WindowState=2 (最小化) 来实现隐藏
                try:
                    presentation = ppt_app.Presentations.Open(
                        working_input_path, 
                        ReadOnly=True,
                        Untitled=False,
                        WithWindow=True
                    )
                except Exception as e:
                    self._log('warning', f"Open WithWindow=True 失败: {e}，尝试无窗口模式...")
                    presentation = ppt_app.Presentations.Open(
                        working_input_path, 
                        ReadOnly=True,
                        Untitled=False,
                        WithWindow=False
                    )
                time.sleep(2)
                
                slide_count = presentation.Slides.Count
                self._log('info', f"演示文稿打开成功，幻灯片数: {slide_count}")
                
                if slide_count == 0:
                    raise Exception("PPT文件没有幻灯片")
                    
            except Exception as e:
                self._log('error', f"打开演示文稿失败: {type(e).__name__}")
                self._log('error', f"错误详情: {e}")
                
                import traceback
                self._log('error', f"错误堆栈:\n{traceback.format_exc()}")
                
                error_msg = "无法打开PPT文件。可能的原因：\n"
                error_msg += "1. 文件已损坏或格式不正确\n"
                error_msg += "2. PowerPoint版本不兼容\n"
                error_msg += "3. 文件被密码保护\n"
                error_msg += "4. 文件正在被其他程序使用\n"
                error_msg += f"\n原始错误: {str(e)}"
                
                raise Exception(error_msg)
            
            # 处理受保护视图 (Protected View)
            # 即使 Unblock-File 执行了，有时可能仍会进入受保护视图
            if ppt_app.ProtectedViewWindows.Count > 0:
                print(f"[PptToVideo] Protected View detected for {working_input_path}")
                try:
                    pv_window = ppt_app.ProtectedViewWindows(1)
                    if pv_window:
                        # 检查是否是当前文件的窗口
                        # 注意：如果多个文件同时打开，这里可能需要遍历
                        presentation = pv_window.Edit() # 这会返回一个新的可编辑 Presentation 对象
                        print("[PptToVideo] Successfully enabled editing from Protected View")
                except Exception as e:
                     print(f"[PptToVideo] Error editing Protected View: {e}")
                     # 尝试继续，也许 presentation 变量仍然可用？通常不可用。
                     # 如果Edit失败，通常意味着无法转换
                     raise Exception(f"Cannot exit Protected View: {e}")
            
            self.update_progress(input_path, 40)
            
            # 导出视频
            # ppSaveAsMP4 = 39, ppSaveAsWMV = 37
            output_format = 39  # MP4
            
            # 配置视频参数 - 优化默认值以加快速度
            resolution = options.get('resolution', 720)  # 默认 720p（从1080p降低）
            quality = options.get('quality', 50)  # 默认质量（从60降低到50）
            
            # 使用临时输出文件（纯ASCII路径），避免输出路径的中文/编码问题
            temp_output_name = f"ppt_out_{uuid.uuid4().hex}.mp4"
            temp_output_path = os.path.join(temp_dir, temp_output_name)
            print(f"[PptToVideo] Exporting to temp video: {temp_output_path}")
            
            # 激活窗口，确保它在前台（某些环境下必要）
            try:
                if presentation.Windows.Count > 0:
                    presentation.Windows(1).Activate()
                    # ppWindowMaximized = 3
                    presentation.Windows(1).WindowState = 3
            except:
                pass

            # CreateVideo(FileName, UseTimingsAndNarrations, DefaultSlideDuration, VertResolution, FramesPerSecond, Quality)
            # UseTimingsAndNarrations: Default True
            # DefaultSlideDuration: Default 5 seconds
            # VertResolution: 1080, 720, 480...
            # FramesPerSecond: Default 30
            # Quality: 1-100
            
            # 优化视频参数以加快转换速度
            use_timings = options.get('use_timings', False)  # 改为False，不使用PPT内置时间
            fps = options.get('fps', 24)  # 从30降低到24帧，减少渲染量
            default_slide_duration = options.get('slide_duration', 3)  # 从5秒改为3秒，加快速度
            
            try:
                # 尝试使用 CreateVideo 方法
                presentation.CreateVideo(temp_output_path, use_timings, default_slide_duration, resolution, fps, quality)
                
                self.update_progress(input_path, 50)
                
                # 等待导出完成
                start_time = time.time()
                last_progress_update = start_time
                
                while True:
                    time.sleep(2)  # 每2秒检查一次，减少CPU占用
                    
                    try:
                        status = presentation.CreateVideoStatus
                        
                        # 更新进度（每10秒更新一次）
                        if time.time() - last_progress_update > 10:
                            elapsed = time.time() - start_time
                            # 估算进度：假设最多需要5分钟
                            estimated_progress = min(50 + int((elapsed / 300) * 45), 95)
                            self.update_progress(input_path, estimated_progress)
                            last_progress_update = time.time()
                            print(f"[PptToVideo] Status: {status}, Elapsed: {int(elapsed)}s")
                        
                        if status == 3: # Done
                            print(f"[PptToVideo] Video creation completed successfully")
                            break
                        elif status == 4: # Failed
                            raise Exception("PowerPoint reported video creation failure (Status=4)")
                        elif status == 0: # None
                             if time.time() - start_time > 10:
                                 if os.path.exists(temp_output_path) and os.path.getsize(temp_output_path) > 0:
                                     print(f"[PptToVideo] Output file exists, assuming success")
                                     break 
                                 elif time.time() - start_time > 60:
                                     raise Exception("Video export failed to start (Status remains 0)")
                    except Exception as e:
                        print(f"[PptToVideo] Error checking status: {e}")
                        # 异常情况下，尝试 SaveAs 作为回退
                        raise e 
                        
                    # 超时保护：10分钟
                    if time.time() - start_time > 600:
                        raise Exception("Video export timed out after 10 minutes")
                        
            except Exception as e:
                print(f"[PptToVideo] CreateVideo failed: {e}. Trying SaveAs fallback...")
                
                # 回退策略：尝试使用 SaveAs 方法导出 MP4
                # ppSaveAsMP4 = 39
                try:
                    # 先删除可能存在的空文件
                    if os.path.exists(temp_output_path):
                        try: os.remove(temp_output_path)
                        except: pass
                        
                    presentation.SaveAs(temp_output_path, 39)
                    
                    # SaveAs 是异步的吗？通常是同步的，但对于视频导出可能会立即返回
                    # 轮询文件直到不再增长
                    start_time = time.time()
                    last_size = -1
                    stable_count = 0
                    
                    while True:
                        time.sleep(2)
                        if not os.path.exists(temp_output_path):
                            if time.time() - start_time > 30: # 30秒还没文件，失败
                                raise Exception("SaveAs failed to create output file")
                            continue
                            
                        current_size = os.path.getsize(temp_output_path)
                        if current_size == last_size and current_size > 0:
                            stable_count += 1
                            if stable_count >= 5: # 10秒大小不变，认为完成
                                break
                        else:
                            last_size = current_size
                            stable_count = 0
                            self.update_progress(input_path, 75) # 模拟进度
                            
                        if time.time() - start_time > 600:
                             raise Exception("SaveAs video export timed out")
                             
                except Exception as save_err:
                    raise Exception(f"Both CreateVideo and SaveAs failed. CreateVideo error: {e}. SaveAs error: {save_err}")

            # 转换成功，将临时文件移动到最终目标
            if os.path.exists(temp_output_path):
                # 确保目标目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                # 移动覆盖
                if os.path.exists(output_path):
                    try: os.remove(output_path)
                    except: pass
                shutil.move(temp_output_path, output_path)
                print(f"[PptToVideo] Moved temp output to: {output_path}")
            else:
                raise Exception("Output file missing after conversion")

            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': os.path.getsize(output_path)
            }
            
        except Exception as e:
            raise Exception(f"PPT to Video failed: {str(e)}")
            
        finally:
            # 清理
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
            
            # 清理临时文件
            try:
                if 'working_input_path' in locals() and working_input_path != input_path:
                    os.remove(working_input_path)
            except:
                pass
