# 文档转换器 (Document Converter)

全能在线文件格式转换工具，支持 DOCX/PDF/HTML/JSON/XML/TXT/PPT/Excel 等格式互转。

## 快速启动

### 1. 后端服务

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端默认运行在 **http://localhost:8002**

### 2. 前端开发服务

```bash
cd frontend
npm install
npm run dev
```

启动后访问: **[http://localhost:5176](http://localhost:5176)**

> `localhost:5176` 和 `127.0.0.1:5176` 均可访问。

### 3. 一键启动（Windows）

```bash
# 后端
start "Backend" cmd /c "cd backend && python main.py"

# 前端
start "Frontend" cmd /c "cd frontend && npm run dev"
```

## 使用说明

1. 打开 [http://localhost:5176](http://localhost:5176)
2. **登录鲲穹账号**（首次使用需登录）
3. 选择转换类别，上传文件
4. 点击「开始转换」，完成后下载结果

## 技术栈

- **前端**: React + Vite + Ant Design + Zustand + i18next
- **后端**: Python FastAPI
- **转换引擎**: pikepdf, pdfminer, openpyxl, python-pptx, Edge headless

## 项目结构

```
文档转换器/
├── backend/          # FastAPI 后端
│   ├── converters/   # 各类转换器
│   ├── main.py       # 入口
│   └── downloads/    # 临时下载目录
├── frontend/         # React 前端
│   ├── src/
│   │   ├── components/  # UI 组件
│   │   ├── pages/       # 页面
│   │   ├── stores/      # Zustand 状态管理
│   │   ├── services/    # API 服务
│   │   └── locales/     # 多语言 (28 种语言)
│   └── vite.config.js
└── README.md
```
