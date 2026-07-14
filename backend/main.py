# backend/main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.routes import router, user_center_service
from backend.services.converter_service import DOWNLOAD_DIR
from backend.utils.logger import logger
from backend.utils.cleanup import cleanup_service

app = FastAPI(title="Format Converter API")

# 配置 CORS
default_cors_origins = [
    "http://localhost:5173",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5176",
    "http://localhost:8002",
    "http://127.0.0.1:8002",
]
extra_cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOW_ORIGINS", "").split(",")
    if origin.strip()
]
allowed_cors_origins = list(dict.fromkeys(default_cors_origins + extra_cors_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录以供下载
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")

# 注册路由
app.include_router(router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    logger.info("后端服务正在启动...")
    logger.info(f"Python 路径: {sys.path}")
    logger.info(f"下载目录: {DOWNLOAD_DIR}")
    try:
        user_center_service.ensure_schema()
        logger.info("用户中心数据表结构检查完成")
    except Exception as exc:
        logger.warning(f"用户中心数据表预热失败: {exc}")
    # 启动清理服务
    cleanup_service.start()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("后端服务正在关闭...")
    # 停止清理服务
    cleanup_service.stop()

if __name__ == "__main__":
    for route in app.routes:
        if hasattr(route, "methods"):
            logger.debug(f"Route: {route.path} {route.methods}")
        else:
            logger.debug(f"Route: {route.path} (Mount)")
    is_frozen = getattr(sys, "frozen", False)
    port = int(os.environ.get("BACKEND_PORT", "8002"))
    logger.info(f"启动端口: {port}, 是否打包: {is_frozen}")
    if is_frozen:
        # 增加超时时间以支持长时间转换（如PPT转视频）
        uvicorn.run(app, host="0.0.0.0", port=port, reload=False, timeout_keep_alive=900)
    else:
        # 开发环境也增加超时
        uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True, timeout_keep_alive=900)
