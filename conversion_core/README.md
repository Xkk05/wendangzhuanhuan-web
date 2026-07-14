# 文档转换核心逻辑库

一个功能强大的Python文档转换库，支持多种格式互转（PDF、Word、Excel、PPT、Image、HTML、Markdown、Text）和OCR识别功能。

## 功能特性

### 📄 文档格式转换（9个转换器）

- **Word转换器** - PDF/Excel/PPT/Word/Image → Word (DOCX/DOC)
- **Excel转换器** - PDF/PPT/Word/Image → Excel (XLSX/XLS)
- **PPT转换器** - PDF/Excel/Word/Image → PPT (PPTX/PPT)
- **Image转换器** - PDF/Excel/PPT/Word → Image (PNG/JPG/BMP/WEBP/GIF)
- **PDF转换器** - Office/Image/Text/HTML/Markdown/CSV/Code → PDF
- **HTML转换器** - PDF/Excel/PPT/Word → HTML
- **Markdown转换器** - PDF → Markdown
- **Text转换器** - PDF/Excel/PPT/Word → Text

### 🔍 OCR识别服务

- 集成**百度千帆OCR**：DeepSeek-OCR、PaddleOCR-VL、PP-StructureV3
- 支持**LaTeX公式识别**和渲染
- 支持**印章识别**和提取
- 支持**表格识别**（HTML表格、Markdown表格）
- 自动**去重**和**版面分析**

### 🛠️ PDF专用工具

- PDF **合并/拆分**
- PDF **压缩**（智能压缩策略）
- PDF **解密**（移除密码保护）
- PDF **提取页面**
- PDF **信息获取**

### 💼 Office转换工具

- **Office → PDF**：支持COM（Windows）和LibreOffice（跨平台）双策略
- 自动检测可用转换方法
- 打包环境支持

## 安装

### 1. 安装Python依赖

```bash
cd conversion_core
pip install -r requirements.txt
```

### 2. 安装可选依赖

#### Windows系统（Office COM）

```bash
pip install pywin32
```

#### 跨平台（LibreOffice）

下载并安装 [LibreOffice](https://www.libreoffice.org/)

#### HTML高级转PDF

安装 Chrome 或 Edge 浏览器

## 快速入门

### 1. PDF转Word

```python
from conversion_core import WordConverter

# 创建转换器
config = {
    'output_format': 'docx',  # 或 'doc'
    'extract_images': True,    # 提取图片
    'extract_tables': True     # 提取表格
}

converter = WordConverter(
    output_path='./output',
    config=config,
    progress_callback=lambda file, progress: print(f'进度: {progress}%')
)

# 转换文件
result = converter.convert('example.pdf')

if result['success']:
    print(f'转换成功: {result["output_file"]}')
else:
    print(f'转换失败: {result["error"]}')
```

### 2. Office转PDF

```python
from conversion_core import PDFConverter

config = {}
converter = PDFConverter(output_path='./output', config=config)

# Word/Excel/PPT都支持
result = converter.convert('document.docx')
print(f'输出文件: {result["output_file"]}')
```

### 3. OCR识别（需要API密钥）

```python
from conversion_core import OCRConversionService, OCRConfig

# 配置OCR服务
config = {
    'model': 'auto',          # 自动选择模型
    'has_seal': True,         # 识别印章
    'has_formula': True,      # 识别公式
    'has_chart': False,       # 识别图表
    'target_format': 'word',  # 输出格式 (word/excel)
    'output_dir': './output'
}

service = OCRConversionService(
    api_key='your_baidu_qianfan_api_key',  # 百度千帆 API Key
    config=config
)

# 转换PDF
result = service.convert(
    file_path='scan.pdf',
    progress_callback=lambda current, total, msg: print(f'{current}/{total}: {msg}')
)

if result['success']:
    print(f'OCR成功: {result["output_file"]}')
```

### 4. PDF工具箱

```python
from conversion_core import PDFTools

# 合并PDF
result = PDFTools.merge_pdfs(
    file_list=['file1.pdf', 'file2.pdf', 'file3.pdf'],
    output_path='merged.pdf'
)

# 拆分PDF
result = PDFTools.split_pdf(
    input_path='large.pdf',
    output_dir='./split_output',
    split_mode='pages',
    pages_per_file=10
)

# 压缩PDF
result = PDFTools.compress_pdf(
    input_path='large.pdf',
    output_path='compressed.pdf',
    image_quality=75
)

# 解密PDF
result = PDFTools.unlock_pdf(
    input_path='encrypted.pdf',
    output_path='unlocked.pdf',
    password='your_password'
)
```

## 高级用法

### 批量转换

```python
from conversion_core import PDFConverter
from pathlib import Path

converter = PDFConverter(output_path='./output', config={})

# 批量处理目录下所有Word文件
input_dir = Path('./documents')
for file in input_dir.glob('*.docx'):
    result = converter.convert(str(file))
    print(f'{file.name} -> {result["output_file"]}')
```

### 自定义进度回调

```python
def progress_callback(file_path, progress):
    """自定义进度回调"""
    filename = Path(file_path).name
    bar_length = 40
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f'\r{filename}: [{bar}] {progress}%', end='', flush=True)

converter = WordConverter(
    output_path='./output',
    config={},
    progress_callback=progress_callback
)
```

### 错误处理

```python
try:
    result = converter.convert('input.pdf')
    
    if result['success']:
        print('转换成功')
    else:
        # 处理转换失败
        error_msg = result.get('error', '未知错误')
        print(f'转换失败: {error_msg}')
        
except FileNotFoundError:
    print('文件不存在')
except Exception as e:
    print(f'发生异常: {e}')
```

## API文档

### 转换器基类 (Converter)

所有转换器的基类，定义了通用接口。

#### 构造函数

```python
Converter(output_path, config, progress_callback=None)
```

**参数:**
- `output_path` (str): 输出目录路径
- `config` (dict): 转换配置
- `progress_callback` (callable, 可选): 进度回调函数 `(file_path, progress) -> None`

#### convert()

```python
convert(file_path: str) -> dict
```

执行转换。

**返回:**
```python
{
    'success': bool,        # 是否成功
    'output_file': str,     # 输出文件路径
    'error': str           # 错误信息（如果失败）
}
```

### WordConverter

PDF/Excel/PPT/Image → Word 转换器

**配置选项:**
```python
config = {
    'output_format': 'docx',      # 输出格式: 'docx' 或 'doc'
    'extract_images': True,        # 提取图片
    'extract_tables': True,        # 提取表格
    'page_range': '1-10,15,20'    # 页面范围（PDF转换）
}
```

### ExcelConverter

PDF/PPT/Word/Image → Excel 转换器

**配置选项:**
```python
config = {
    'output_format': 'xlsx',      # 输出格式: 'xlsx' 或 'xls'
    'mode': 'ocr'                 # PDF转换模式: 'extract' 或 'ocr'
}
```

### PDFConverter

Office/Image/Text/HTML/Markdown/CSV/Code → PDF 转换器

**配置选项:**
```python
config = {
    'prefer_office': True,        # 优先使用Office COM（Windows）
    'image_quality': 95,          # 图片质量（1-100）
    'paper_size': 'A4'           # 纸张大小
}
```

### ImageConverter

PDF/Excel/PPT/Word → Image 转换器

**配置选项:**
```python
config = {
    'output_format': 'png',       # 格式: 'png', 'jpg', 'bmp', 'webp', 'gif'
    'quality': 'high',            # 质量: 'ultra', 'high', 'medium'
    'dpi': 200,                   # DPI分辨率
    'transparent': False,         # 透明背景
    'lossless': False            # 无损压缩
}
```

### OCRConversionService

OCR识别服务

**配置选项:**
```python
config = {
    'model': 'auto',              # 模型: 'auto', 'deepseek-ocr', 'paddleocr-vl', 'pp-structurev3'
    'has_seal': True,             # 识别印章
    'has_formula': True,          # 识别公式
    'has_chart': False,           # 识别图表
    'target_format': 'word',      # 输出格式: 'word' 或 'excel'
    'output_dir': './output'
}
```

### PDFTools

PDF工具类（所有方法都是静态方法）

#### merge_pdfs()

```python
PDFTools.merge_pdfs(file_list: List[str], output_path: str) -> dict
```

合并多个PDF文件。

#### split_pdf()

```python
PDFTools.split_pdf(
    input_path: str, 
    output_dir: str,
    split_mode: str = 'pages',  # 模式: 'pages', 'size', 'custom'
    **kwargs
) -> dict
```

拆分PDF文件。

#### compress_pdf()

```python
PDFTools.compress_pdf(
    input_path: str, 
    output_path: str,
    image_quality: int = 75
) -> dict
```

压缩PDF文件。

#### unlock_pdf()

```python
PDFTools.unlock_pdf(
    input_path: str,
    output_path: str,
    password: str
) -> dict
```

解除PDF密码保护。

## 注意事项

### 系统要求

- **Python**: 3.8+
- **操作系统**: Windows / Linux / macOS

### 依赖说明

1. **OCR功能**需要百度千帆API密钥
2. **Office转PDF on Windows**需要安装Microsoft Office
3. **Office转PDF跨平台**需要安装LibreOffice
4. **HTML高级转PDF**需要Chrome或Edge浏览器

### 常见问题

**Q: PDF转Word时图片显示为黑色？**

A: 这是透明背景图片的问题。库已自动处理透明通道，将透明背景合成为白色。

**Q: Office转PDF失败？**

A: 检查是否安装了Office（Windows）或LibreOffice（跨平台）。可以通过`OfficeToPDF.check_office_available()`检测。

**Q: OCR识别失败？**

A: 
1. 检查API密钥是否正确
2. 检查网络连接
3. 查看错误码和错误信息

**Q: 大文件处理很慢？**

A: 大文件（>50MB或>10页）会自动分块处理。可以通过进度回调监控进度。

## 项目结构

```
conversion_core/
├── core/              # 核心转换器
│   ├── base.py
│   ├── converter_word.py
│   ├── converter_excel.py
│   ├── converter_ppt.py
│   ├── converter_image.py
│   ├── converter_pdf.py
│   ├── converter_html.py
│   ├── converter_markdown.py
│   └── converter_text.py
│
├── ocr/               # OCR服务
│   ├── ocr_service.py
│   ├── ocr_conversion_service.py
│   ├── ocr_word_generator.py
│   └── ocr_excel_generator.py
│
├── tools/             # 专用工具
│   ├── office_to_pdf.py
│   └── pdf_tools.py
│
├── services/          # 辅助服务
│   ├── markdown_parser.py
│   ├── retry_strategy.py
│   ├── pdf_validator.py
│   └── api_key_manager.py
│
└── examples/          # 使用示例
    ├── quick_start.py
    ├── pdf_to_word.py
    ├── ocr_example.py
    └── batch_convert.py
```

## 更新日志

### v1.0.0 (2026-01-16)

- ✨ 首次发布
- 支持8种文档格式互转
- 集成百度千帆OCR
- 提供PDF工具箱
- 支持跨平台Office转换

## 许可证

本项目提取自 `pdf-tool-box` 项目。

## 支持

如有问题或建议，请联系开发团队。

---

**Made with ❤️ for the team**
