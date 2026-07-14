# backend/utils/file_handler.py
import os
import shutil
from fastapi import UploadFile
import uuid

class FileHandler:
    """文件处理工具"""
    
    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
    
    async def save_upload_file(self, upload_file: UploadFile) -> str:
        """保存上传的文件并返回路径"""
        ext = upload_file.filename.split('.')[-1] if '.' in upload_file.filename else ''
        unique_filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        return file_path
    
    def cleanup_file(self, file_path: str):
        """删除文件"""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清理文件名，移除路径分隔符和非法字符
        """
        if not filename:
            return "untitled"
            
        import re
        # 1. 获取文件名部分 (处理路径注入)
        filename = os.path.basename(filename)
        
        # 2. 移除Windows非法字符: < > : " / \ | ? *
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # 3. 移除控制字符
        filename = re.sub(r'[\x00-\x1f]', '', filename)
        
        # 4. 移除首尾空白和点
        filename = filename.strip().strip('.')
        
        if not filename:
            return "untitled"
            
        return filename
