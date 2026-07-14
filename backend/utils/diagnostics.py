import os
import sys
import platform
import subprocess
import shutil
from typing import Dict, Any

def check_office_installed() -> Dict[str, Any]:
    """检查 Office 组件是否安装"""
    results = {
        'word': False,
        'excel': False,
        'ppt': False,
        'wps': False
    }
    
    if platform.system() != 'Windows':
        return results
        
    try:
        import win32com.client
        import pythoncom
        
        pythoncom.CoInitialize()
        
        # 检查 Word
        try:
            word = win32com.client.Dispatch("Word.Application")
            results['word'] = True
            word.Quit()
        except:
            pass
            
        # 检查 Excel
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            results['excel'] = True
            excel.Quit()
        except:
            pass
            
        # 检查 PPT
        try:
            ppt = win32com.client.Dispatch("PowerPoint.Application")
            results['ppt'] = True
            ppt.Quit()
        except:
            pass
            
        pythoncom.CoUninitialize()
    except Exception as e:
        print(f"COM Check failed: {e}")

    # 检查 WPS (简单通过注册表或文件路径，这里简单化)
    wps_paths = [
        r"C:\Program Files\Kingsoft\WPS Office\ksolaunch.exe",
        r"C:\Program Files (x86)\Kingsoft\WPS Office\ksolaunch.exe"
    ]
    for path in wps_paths:
        if os.path.exists(path):
            results['wps'] = True
            break
            
    return results

def check_browsers() -> Dict[str, Any]:
    """检查浏览器是否安装 (用于 HTML 转换)"""
    results = {
        'chrome': False,
        'edge': False
    }
    
    if platform.system() == 'Windows':
        paths = {
            'chrome': [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ],
            'edge': [
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            ]
        }
        
        for browser, browser_paths in paths.items():
            for path in browser_paths:
                if os.path.exists(path):
                    results[browser] = True
                    break
    
    # 也可以通过 which 检查
    if not results['chrome'] and shutil.which('chrome'):
        results['chrome'] = True
    if not results['chrome'] and shutil.which('google-chrome'):
        results['chrome'] = True
    if not results['chrome'] and shutil.which('chromium'):
        results['chrome'] = True
    if not results['chrome'] and shutil.which('chromium-browser'):
        results['chrome'] = True
    if not results['edge'] and shutil.which('msedge'):
        results['edge'] = True
    if not results['edge'] and shutil.which('microsoft-edge'):
        results['edge'] = True
        
    return results

def get_system_info() -> Dict[str, Any]:
    """获取系统基本信息"""
    return {
        'os': platform.system(),
        'os_release': platform.release(),
        'os_version': platform.version(),
        'architecture': platform.machine(),
        'python_version': sys.version,
        'is_frozen': getattr(sys, 'frozen', False),
        'executable': sys.executable
    }

def run_all_diagnostics() -> Dict[str, Any]:
    """运行所有诊断"""
    return {
        'system': get_system_info(),
        'office': check_office_installed(),
        'browsers': check_browsers(),
        'env_vars': {k: v for k, v in os.environ.items() if 'BACKEND' in k or 'PORT' in k}
    }
