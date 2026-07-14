import os
import sys
import logging
import tempfile
from datetime import datetime

def setup_logger(name):
    """设置日志记录器，支持打包后的环境"""
    # 确定日志目录
    configured_log_dir = os.environ.get("BACKEND_LOG_DIR")
    if configured_log_dir:
        log_dir = os.path.abspath(configured_log_dir)
    elif getattr(sys, 'frozen', False):
        # 打包环境：使用系统临时目录
        log_dir = os.path.join(tempfile.gettempdir(), 'doc-converter', 'logs')
    else:
        # 开发环境：使用项目根目录下的 logs
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    
    try:
        os.makedirs(log_dir, exist_ok=True)
    except:
        # 如果无法创建目录，回退到临时目录根
        log_dir = tempfile.gettempdir()

    log_file = os.path.join(log_dir, f'{name}_{datetime.now().strftime("%Y%m%d")}.log')
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 清除已有的处理器
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # 文件处理器
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"无法创建日志文件: {e}")
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger

# 创建通用 logger
logger = setup_logger('backend')
