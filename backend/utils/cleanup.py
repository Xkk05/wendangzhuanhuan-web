import os
import time
import threading
from backend.services.converter_service import UPLOAD_DIR, DOWNLOAD_DIR
from backend.utils.logger import logger

class CleanupService:
    def __init__(self, interval_seconds=3600, max_age_seconds=86400):
        """
        初始化清理服务
        :param interval_seconds: 检查间隔（秒），默认1小时
        :param max_age_seconds: 文件最大保留时间（秒），默认24小时
        """
        self.interval_seconds = interval_seconds
        self.max_age_seconds = max_age_seconds
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        """启动后台清理线程"""
        if not self.thread.is_alive():
            self.thread.start()
            logger.info("临时文件清理服务已启动")

    def stop(self):
        """停止后台清理线程"""
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=5)
            logger.info("临时文件清理服务已停止")

    def _run(self):
        """后台运行逻辑"""
        logger.info(f"清理服务已启动，将在后台运行。间隔: {self.interval_seconds}s, 过期时间: {self.max_age_seconds}s")
        while not self.stop_event.is_set():
            try:
                self._cleanup_directory(UPLOAD_DIR)
                self._cleanup_directory(DOWNLOAD_DIR)
            except Exception as e:
                logger.error(f"清理过程中发生错误: {e}")
            
            # 等待下一次检查，或者收到停止信号
            if self.stop_event.wait(self.interval_seconds):
                break

    def _cleanup_directory(self, directory):
        """清理指定目录下的过期文件"""
        if not os.path.exists(directory):
            return

        now = time.time()
        count = 0
        
        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                # 跳过目录
                if os.path.isdir(file_path):
                    continue
                    
                try:
                    # 获取文件修改时间
                    file_age = now - os.path.getmtime(file_path)
                    
                    if file_age > self.max_age_seconds:
                        os.remove(file_path)
                        count += 1
                        logger.debug(f"已删除过期文件: {filename}")
                except Exception as e:
                    logger.warning(f"无法删除文件 {filename}: {e}")
        except Exception as e:
             logger.error(f"遍历目录失败 {directory}: {e}")
                
        if count > 0:
            logger.info(f"清理了 {directory} 中的 {count} 个过期文件")

# 全局单例
cleanup_service = CleanupService(interval_seconds=3600, max_age_seconds=86400)
