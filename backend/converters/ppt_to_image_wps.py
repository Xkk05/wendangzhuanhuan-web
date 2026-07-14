"""
PPT转图片转换器 - 使用WPS直接导出
支持PNG和JPG格式
"""

import os
import time
import shutil
import zipfile
from typing import Dict, Any
from .base import BaseConverter


class PptToImageWpsConverter(BaseConverter):
    """PPT转图片转换器（使用WPS）"""
    
    def __init__(self):
        super().__init__()
        self.office_type = self._detect_office()
        
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
                print(f"[PptToImageWps] 检测到 Microsoft PowerPoint {version}")
                return "PowerPoint"
            except:
                pass
            
            # 2. 尝试WPS
            for app_name in ['KWPP.Application', 'WPP.Application']:
                try:
                    wps_app = win32com.client.Dispatch(app_name)
                    wps_app.Quit()
                    pythoncom.CoUninitialize()
                    print(f"[PptToImageWps] 检测到 WPS Office ({app_name})")
                    return app_name
                except:
                    continue
            
            pythoncom.CoUninitialize()
            
        except ImportError:
            pass
        
        return None
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """转换PPT为图片"""
        
        print(f"[PptToImageWps] 开始转换: {input_path}")
        print(f"[PptToImageWps] 使用: {self.office_type or '未检测到Office软件'}")
        
        self.validate_input(input_path)
        self.update_progress(input_path, 5)
        
        if not self.office_type:
            raise Exception("未检测到PowerPoint或WPS。请安装其中之一")
        
        try:
            import win32com.client
            import pythoncom
        except ImportError:
            raise Exception("pywin32未安装")
        
        # 获取目标格式
        target_format = os.path.splitext(output_path)[1].lower()[1:]  # 去掉点号
        if target_format not in ['png', 'jpg', 'jpeg']:
            target_format = 'png'
        
        # 标准化格式名称
        if target_format == 'jpeg':
            target_format = 'jpg'
        
        format_upper = target_format.upper()
        
        print(f"[PptToImageWps] 目标格式: {format_upper}")
        
        # 导出图片
        image_files = []
        last_error = None
        
        try:
            if self.office_type == "PowerPoint":
                print(f"[PptToImageWps] 尝试使用 PowerPoint...")
                image_files = self._ppt_to_images_powerpoint(input_path, format_upper)
            else:
                print(f"[PptToImageWps] 尝试使用 WPS...")
                image_files = self._ppt_to_images_wps(input_path, format_upper)
        except Exception as e:
            last_error = e
            print(f"[PptToImageWps] {self.office_type} 失败: {e}")
            
            # 如果PowerPoint失败，尝试WPS
            if self.office_type == "PowerPoint":
                print(f"[PptToImageWps] 回退到 WPS...")
                try:
                    # 重新检测WPS
                    pythoncom.CoInitialize()
                    for app_name in ['KWPP.Application', 'WPP.Application']:
                        try:
                            test_app = win32com.client.Dispatch(app_name)
                            test_app.Quit()
                            self.office_type = app_name
                            print(f"[PptToImageWps] 找到 WPS: {app_name}")
                            break
                        except:
                            continue
                    pythoncom.CoUninitialize()
                    
                    if self.office_type in ['KWPP.Application', 'WPP.Application']:
                        image_files = self._ppt_to_images_wps(input_path, format_upper)
                except Exception as e2:
                    print(f"[PptToImageWps] WPS 也失败: {e2}")
                    raise Exception(f"PowerPoint和WPS都无法转换: PowerPoint错误={last_error}, WPS错误={e2}")
        
        if not image_files:
            raise Exception(f"未能生成图片。最后错误: {last_error}")
        
        print(f"[PptToImageWps] 生成了 {len(image_files)} 张图片")
        self.update_progress(input_path, 80)
        
        # 如果只有一张图片，直接返回
        if len(image_files) == 1:
            shutil.move(image_files[0], output_path)
            self.update_progress(input_path, 100)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': os.path.getsize(output_path),
                'pages': 1,
                'converter': self.office_type
            }
        
        # 多张图片，打包成ZIP
        zip_path = output_path.replace(f'.{target_format}', '.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for img_file in image_files:
                zipf.write(img_file, os.path.basename(img_file))
        
        # 清理临时图片
        for img_file in image_files:
            try:
                os.remove(img_file)
            except:
                pass
        
        self.update_progress(input_path, 100)
        print(f"[PptToImageWps] 转换完成: {zip_path}")
        
        return {
            'success': True,
            'output_path': zip_path,
            'size': os.path.getsize(zip_path),
            'pages': len(image_files),
            'converter': self.office_type
        }
    
    def _kill_process(self, process_name: str):
        """强制结束进程"""
        try:
            os.system(f"taskkill /f /im {process_name} >nul 2>&1")
        except:
            pass

    def _configure_hidden_wps(self, wps_app) -> bool:
        """Prefer hidden WPS mode and fall back to minimized mode only if needed."""
        try:
            wps_app.DisplayAlerts = 0
        except Exception as e:
            print(f"[PptToImageWps] Failed to disable WPS alerts: {e}")

        for visible_value in (0, False):
            try:
                wps_app.Visible = visible_value
                return True
            except Exception:
                continue

        try:
            wps_app.Visible = 1
            wps_app.WindowState = 2
        except Exception as e:
            print(f"[PptToImageWps] Failed to minimize WPS window: {e}")
        return False

    def _ppt_to_images_powerpoint(self, ppt_path: str, format_type: str) -> list:
        """使用PowerPoint导出图片"""
        
        import win32com.client
        import pythoncom
        import tempfile
        import shutil
        
        # 转换前尝试清理残留进程
        self._kill_process("POWERPNT.EXE")
        time.sleep(1)
        
        # 确保COM在当前线程初始化
        pythoncom.CoInitialize()
        ppt_app = None
        presentation = None
        temp_input_path = None
        
        try:
            abs_path = os.path.abspath(ppt_path)
            if not os.path.exists(abs_path):
                raise Exception(f"文件不存在: {abs_path}")
            
            # 复制到临时文件以避免权限/锁定问题
            temp_input_path = os.path.join(tempfile.gettempdir(), f"temp_ppt_{int(time.time())}{os.path.splitext(ppt_path)[1]}")
            shutil.copy2(abs_path, temp_input_path)
            print(f"[PptToImageWps] 临时文件已创建: {temp_input_path}")
                
            print(f"[PptToImageWps] 启动 PowerPoint...")
            # 使用DispatchEx创建新实例，避免复用可能有问题的实例
            try:
                ppt_app = win32com.client.DispatchEx("PowerPoint.Application")
            except:
                # 如果DispatchEx失败，回退到Dispatch
                ppt_app = win32com.client.Dispatch("PowerPoint.Application")
            
            # 设置PowerPoint属性
            try:
                # 优先显示并最小化，这在旧版 PowerPoint 中最稳定
                ppt_app.Visible = 1
                ppt_app.WindowState = 2 # 最小化
                ppt_app.DisplayAlerts = 0
            except Exception as e:
                print(f"[PptToImageWps] 无法设置PowerPoint窗口状态: {e}")
                
            # 打开文件
            print(f"[PptToImageWps] 打开文件 (Minimized): {temp_input_path}")
            try:
                # 对于旧版 PowerPoint (如 2007/12.0)，WithWindow=False 可能导致 Export 失败
                # 因此我们优先使用 WithWindow=True，配合之前的 WindowState=2 (最小化) 来实现隐藏
                presentation = ppt_app.Presentations.Open(
                    FileName=temp_input_path,
                    ReadOnly=True,
                    Untitled=False,
                    WithWindow=True
                )
            except Exception as e:
                print(f"[PptToImageWps] Open WithWindow=True 失败: {e}, 尝试无窗口模式")
                try:
                    presentation = ppt_app.Presentations.Open(
                        FileName=temp_input_path,
                        ReadOnly=True,
                        Untitled=False,
                        WithWindow=False
                    )
                except Exception as e2:
                    print(f"[PptToImageWps] Open失败: {e2}")
                    raise e2
            
            time.sleep(1)
            
            slide_count = presentation.Slides.Count
            print(f"[PptToImageWps] PowerPoint: {slide_count} 页")
            
            # 创建临时目录
            temp_dir = os.path.join(os.path.dirname(ppt_path), f"temp_images_{int(time.time())}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 策略调整：优先使用 Export 逐页导出以保证清晰度 (1920x1080)
            # 只有当 Export 失败时，才回退到 SaveAs
            print(f"[PptToImageWps] 尝试逐页高清导出 (1920x1080)...")
            image_files = []
            use_fallback = False

            try:
                for i in range(1, slide_count + 1):
                    slide = presentation.Slides(i)
                    output_file = os.path.join(temp_dir, f"slide_{i:04d}.{format_type.lower()}")
                    
                    try:
                        # 尝试高清导出
                        slide.Export(output_file, format_type, 1920, 1080)
                    except Exception as e:
                        # 如果高清导出失败，尝试默认导出
                        # print(f"[PptToImageWps] Slide {i} 高清导出失败: {e}，尝试默认参数...")
                        slide.Export(output_file, format_type)
                    
                    if os.path.exists(output_file):
                        image_files.append(output_file)
                        if i % 5 == 0 or i == slide_count:
                            print(f"[PptToImageWps] 已导出 {i}/{slide_count}")
                
                if len(image_files) == 0:
                    print(f"[PptToImageWps] 逐页导出未生成文件，切换到 SaveAs 模式")
                    use_fallback = True
                    
            except Exception as e_export:
                print(f"[PptToImageWps] 逐页导出失败: {e_export}，切换到 SaveAs 模式")
                use_fallback = True
                image_files = []

            # 回退策略：SaveAs 批量导出
            if use_fallback:
                # ppSaveAsJPG = 17, ppSaveAsPNG = 18, ppSaveAsBMP = 19
                save_format = 18 if format_type.upper() == 'PNG' else 17
                print(f"[PptToImageWps] 尝试使用 SaveAs 批量导出...")
                
                try:
                    # SaveAs 会创建一个同名文件夹（如果目标是图片格式）
                    # 构造一个不带扩展名的路径，PowerPoint会在其后创建文件夹
                    save_as_path = os.path.join(temp_dir, "export")
                    presentation.SaveAs(save_as_path, save_format)
                    
                    found_images = []
                    # 检查 temp_dir 下是否有名为 export 的文件夹
                    export_folder = save_as_path
                    if os.path.exists(export_folder) and os.path.isdir(export_folder):
                        # 遍历该文件夹
                        for f in os.listdir(export_folder):
                            if f.lower().endswith(f'.{format_type.lower()}'):
                                found_images.append(os.path.join(export_folder, f))
                    
                    if found_images:
                        print(f"[PptToImageWps] SaveAs 成功，找到 {len(found_images)} 张图片")
                        # 简单按长度排序通常能把 Slide1 和 Slide10 分开 (Slide1.jpg vs Slide10.jpg)
                        # 但为了更准确，我们尝试按数字排序
                        try:
                            import re
                            def get_slide_num(filename):
                                match = re.search(r'(\d+)', os.path.basename(filename))
                                return int(match.group(1)) if match else 0
                            image_files = sorted(found_images, key=get_slide_num)
                        except:
                            image_files = sorted(found_images, key=lambda x: len(x))
                    else:
                        print(f"[PptToImageWps] SaveAs 未找到图片")
                except Exception as e_save:
                    print(f"[PptToImageWps] SaveAs 失败: {e_save}")

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
            # 清理临时输入文件
            if temp_input_path and os.path.exists(temp_input_path):
                try:
                    time.sleep(0.5)
                    os.remove(temp_input_path)
                except:
                    pass
            pythoncom.CoUninitialize()
    
    def _ppt_to_images_wps(self, ppt_path: str, format_type: str) -> list:
        """使用WPS导出图片"""
        
        import win32com.client
        import pythoncom
        import tempfile
        import shutil
        
        # 转换前尝试清理残留进程
        self._kill_process("wps.exe")
        
        pythoncom.CoInitialize()
        wps_app = None
        presentation = None
        temp_input_path = None
        
        try:
            abs_path = os.path.abspath(ppt_path)
            if not os.path.exists(abs_path):
                raise Exception(f"文件不存在: {abs_path}")
            
            # 复制到临时文件以避免权限/锁定问题
            temp_input_path = os.path.join(tempfile.gettempdir(), f"temp_wps_{int(time.time())}{os.path.splitext(ppt_path)[1]}")
            shutil.copy2(abs_path, temp_input_path)
            print(f"[PptToImageWps] 临时文件已创建: {temp_input_path}")
            
            print(f"[PptToImageWps] 启动 WPS ({self.office_type})...")
            # 启动WPS
            wps_app = win32com.client.Dispatch(self.office_type)
            
            # WPS建议先可见再最小化
            try:
                wps_app.Visible = 1
                wps_app.WindowState = 2 # 最小化
                wps_app.DisplayAlerts = 0
            except Exception as e:
                print(f"[PptToImageWps] 无法设置WPS窗口状态: {e}")
            
            # 打开文件
            print(f"[PptToImageWps] WPS打开文件 (Minimized): {temp_input_path}")
            try:
                # 优先使用 WithWindow=True 配合最小化，以确保 Export 可用
                presentation = wps_app.Presentations.Open(
                    FileName=temp_input_path,
                    ReadOnly=True,
                    WithWindow=True
                )
            except Exception as e:
                print(f"[PptToImageWps] WPS Open WithWindow=True 失败: {e}, 尝试无窗口模式")
                try:
                    presentation = wps_app.Presentations.Open(
                        FileName=temp_input_path,
                        ReadOnly=True,
                        WithWindow=False
                    )
                except Exception as e2:
                    print(f"[PptToImageWps] WPS Open失败: {e2}")
                    raise e2
            
            time.sleep(1)
            
            slide_count = presentation.Slides.Count
            print(f"[PptToImageWps] WPS: {slide_count} 页")
            
            # 创建临时目录
            temp_dir = os.path.join(os.path.dirname(ppt_path), f"temp_images_{int(time.time())}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 导出图片
            image_files = []
            for i in range(1, slide_count + 1):
                slide = presentation.Slides(i)
                output_file = os.path.join(temp_dir, f"slide_{i:04d}.{format_type.lower()}")
                
                try:
                    slide.Export(output_file, format_type, 1920, 1080)
                except:
                    try:
                        slide.Export(output_file, format_type)
                    except Exception as e:
                        print(f"[PptToImageWps] 第{i}页导出失败: {e}")
                        continue
                
                if os.path.exists(output_file):
                    image_files.append(output_file)
                    if i % 5 == 0 or i == slide_count:
                        print(f"[PptToImageWps] 已导出 {i}/{slide_count}")
            
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
            # 清理临时输入文件
            if temp_input_path and os.path.exists(temp_input_path):
                try:
                    os.remove(temp_input_path)
                except:
                    pass
            pythoncom.CoUninitialize()

    def _ppt_to_images_wps(self, ppt_path: str, format_type: str) -> list:
        """Use WPS in hidden mode first to reduce popup windows."""

        import win32com.client
        import pythoncom
        import tempfile
        import shutil

        self._kill_process("wps.exe")

        pythoncom.CoInitialize()
        wps_app = None
        presentation = None
        temp_input_path = None

        try:
            abs_path = os.path.abspath(ppt_path)
            if not os.path.exists(abs_path):
                raise Exception(f"File not found: {abs_path}")

            temp_input_path = os.path.join(
                tempfile.gettempdir(),
                f"temp_wps_{int(time.time())}{os.path.splitext(ppt_path)[1]}"
            )
            shutil.copy2(abs_path, temp_input_path)
            print(f"[PptToImageWps] Temp file created: {temp_input_path}")

            wps_app = win32com.client.Dispatch(self.office_type)

            hidden_mode = False
            try:
                wps_app.DisplayAlerts = 0
            except Exception as e:
                print(f"[PptToImageWps] Failed to disable alerts: {e}")

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
                    print(f"[PptToImageWps] Failed to minimize WPS: {e}")

            print(f"[PptToImageWps] Opening file in {'hidden' if hidden_mode else 'minimized'} mode: {temp_input_path}")
            try:
                presentation = wps_app.Presentations.Open(
                    FileName=temp_input_path,
                    ReadOnly=True,
                    WithWindow=not hidden_mode
                )
            except Exception as e:
                print(f"[PptToImageWps] Preferred open mode failed: {e}")
                if hidden_mode:
                    try:
                        wps_app.Visible = 1
                        wps_app.WindowState = 2
                    except Exception:
                        pass
                presentation = wps_app.Presentations.Open(
                    FileName=temp_input_path,
                    ReadOnly=True,
                    WithWindow=hidden_mode
                )

            time.sleep(1)

            slide_count = presentation.Slides.Count
            temp_dir = os.path.join(os.path.dirname(ppt_path), f"temp_images_{int(time.time())}")
            os.makedirs(temp_dir, exist_ok=True)

            image_files = []
            for i in range(1, slide_count + 1):
                slide = presentation.Slides(i)
                output_file = os.path.join(temp_dir, f"slide_{i:04d}.{format_type.lower()}")

                try:
                    slide.Export(output_file, format_type, 1920, 1080)
                except Exception:
                    try:
                        slide.Export(output_file, format_type)
                    except Exception as e:
                        print(f"[PptToImageWps] Export failed on slide {i}: {e}")
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
            if temp_input_path and os.path.exists(temp_input_path):
                try:
                    os.remove(temp_input_path)
                except Exception:
                    pass
            pythoncom.CoUninitialize()
