import os
import time
from typing import Dict
from pathlib import Path

def convert_ppt_to_video(input_path: str, output_path: str = None, resolution: int = 1080, quality: int = 85) -> Dict:
    """
    使用 PowerPoint COM 组件将 PPT 转换为视频 (MP4)
    
    Args:
        input_path: PPT文件路径
        output_path: 输出视频路径，如果为None则自动生成
        resolution: 垂直分辨率 (720, 1080, 2160)
        quality: 视频质量 (0-100)
        
    Returns:
        Dict: {'success': bool, 'output_file': str, 'error': str}
    """
    ppt_app = None
    presentation = None
    
    # 检查输入文件
    if not os.path.exists(input_path):
        return {'success': False, 'error': f'输入文件不存在: {input_path}'}
        
    # 确定输出路径
    if not output_path:
        p = Path(input_path)
        output_path = str(p.with_suffix('.mp4'))
    
    # 确保输出目录存在
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    abs_input_path = os.path.abspath(input_path)
    abs_output_path = os.path.abspath(output_path)
    
    try:
        import win32com.client
        
        # 启动 PowerPoint
        try:
            ppt_app = win32com.client.Dispatch('PowerPoint.Application')
        except Exception as e:
            return {'success': False, 'error': f'无法启动 PowerPoint Application: {str(e)}。请确保已安装 Microsoft PowerPoint。'}
            
        # 尝试隐藏 PowerPoint 窗口
        try:
            # 注意：在某些环境下，必须先 Visible = 1 才能设置 WindowState = 2 (最小化)
            # 这比直接设置 Visible = 0 更稳定，能避免 "RPC 服务器不可用" 错误
            ppt_app.Visible = 1
            ppt_app.WindowState = 2 # ppWindowMinimized
            ppt_app.DisplayAlerts = 0
        except Exception as e:
            print(f"[ppt_to_video] 无法设置窗口状态: {e}")
            try:
                ppt_app.Visible = 0
            except:
                pass
            
        # 打开演示文稿
        try:
            # 使用 WithWindow=False 尝试无窗口打开
            presentation = ppt_app.Presentations.Open(abs_input_path, WithWindow=False)
        except Exception as e:
            return {'success': False, 'error': f'无法打开 PPT 文件: {str(e)}'}
        
        # 使用 CreateVideo 方法导出
        # 参数: FileName, UseTimingsAndNarrations, DefaultSlideDuration, VertResolution, FramesPerSecond, Quality
        # DefaultSlideDuration = 5秒
        presentation.CreateVideo(abs_output_path, True, 5, resolution, 30, quality)
        
        # 轮询状态
        # ppMediaTaskStatusNone = 0
        # ppMediaTaskStatusInProgress = 1
        # ppMediaTaskStatusQueued = 2
        # ppMediaTaskStatusDone = 3
        # ppMediaTaskStatusFailed = 4
        
        max_wait = 1800 # 最大等待 30 分钟 (视频导出可能很慢)
        start_time = time.time()
        
        while True:
            # 必须调用 DoEvents 让 PowerPoint 处理消息循环，否则可能卡住
            # 但 python win32com 没有直接的 DoEvents，通常不需要，除非是在 GUI 线程中
            
            status = presentation.CreateVideoStatus
            
            if status == 3: # Done
                break
            
            if status == 4: # Failed
                # 尝试获取更多错误信息（如果有的话）
                return {'success': False, 'error': 'PowerPoint 报告视频导出任务失败'}
            
            if time.time() - start_time > max_wait:
                return {'success': False, 'error': '视频导出超时'}
                
            time.sleep(1)
            
        # 验证输出文件
        if os.path.exists(abs_output_path) and os.path.getsize(abs_output_path) > 0:
            return {'success': True, 'output_file': abs_output_path}
        else:
            return {'success': False, 'error': '导出显示成功但未找到输出文件或文件为空'}
        
    except ImportError:
        return {'success': False, 'error': '缺少 pywin32 库，请安装: pip install pywin32'}
    except Exception as e:
        return {'success': False, 'error': f'转换过程发生未预期的错误: {str(e)}'}
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
