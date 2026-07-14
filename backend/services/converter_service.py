import os
import platform
import uuid
from typing import Dict, Any, List
from backend.utils.file_handler import FileHandler
from backend.converters.json_to_yaml import JsonToYamlConverter
from backend.converters.json_to_xml import JsonToXmlConverter
from backend.converters.xml_to_json import XmlToJsonConverter
from backend.converters.xml_to_yaml import XmlToYamlConverter
from backend.converters.docx_to_txt import DocxToTxtConverter
from backend.converters.docx_to_pdf import DocxToPdfConverter
from backend.converters.docx_to_image import DocxToImageConverter
from backend.converters.docx_to_epub import DocxToEpubConverter
from backend.converters.html_to_pdf import HtmlToPdfConverter
from backend.converters.html_to_txt import HtmlToTxtConverter
from backend.converters.html_to_markdown import HtmlToMarkdownConverter
from backend.converters.html_to_image import HtmlToImageConverter
from backend.converters.html_to_docx import HtmlToDocxConverter
from backend.converters.html_to_json import HtmlToJsonConverter
from backend.converters.html_to_gif import HtmlToGifConverter
from backend.converters.html_to_svg import HtmlToSvgConverter
from backend.converters.pdf_to_txt import PdfToTxtConverter
from backend.converters.pdf_to_json import PdfToJsonConverter
from backend.converters.pdf_to_base64 import PdfToBase64Converter
from backend.converters.pdf_to_md import PdfToMdConverter
from backend.converters.pdf_to_svg import PdfToSvgConverter
from backend.converters.pdf_to_epub import PdfToEpubConverter
from backend.converters.pdf_to_gif import PdfToGifConverter
from backend.converters.pdf_to_webp import PdfToWebpConverter
from backend.converters.txt_to_pdf import TxtToPdfConverter
from backend.converters.txt_to_image import TxtToImageConverter
from backend.converters.txt_to_speech import TxtToSpeechConverter
from backend.converters.txt_to_ascii import TxtToAsciiConverter
from backend.converters.txt_to_binary import TxtToBinaryConverter
from backend.converters.txt_to_csv import TxtToCsvConverter
from backend.converters.txt_to_hex import TxtToHexConverter
from backend.converters.pdf_to_docx import PdfToDocxConverter
from backend.converters.json_to_csv import JsonToCsvConverter
from backend.converters.json_to_pdf import JsonToPdfConverter
from backend.converters.json_to_base64 import JsonToBase64Converter
from backend.converters.xml_to_csv import XmlToCsvConverter
from backend.converters.xml_to_txt import XmlToTxtConverter
from backend.converters.xml_to_pdf import XmlToPdfConverter
from backend.converters.xml_to_xlsx import XmlToXlsxConverter
from backend.converters.txt_to_html import TxtToHtmlConverter
from backend.converters.pdf_to_html import PdfToHtmlConverter
from backend.converters.pdf_to_image import PdfToImageConverter
from backend.converters.pdf_to_ppt import PdfToPptConverter
from backend.converters.json_to_html import JsonToHtmlConverter
from backend.converters.xml_to_html import XmlToHtmlConverter
from backend.converters.json_to_image import JsonToImageConverter
from backend.converters.json_to_svg import JsonToSvgConverter
from backend.converters.xml_to_image import XmlToImageConverter
from backend.converters.xml_to_svg import XmlToSvgConverter
from backend.converters.pdf_to_rtf import PdfToRtfConverter
from backend.converters.excel_to_ppt import ExcelToPptConverter
from backend.converters.pdf_to_excel import PdfToExcelConverter
from backend.converters.docx_to_excel import DocxToExcelConverter
from backend.converters.docx_to_ppt import DocxToPptConverter
from backend.converters.excel_to_pdf import ExcelToPdfConverter
from backend.converters.ppt_to_pdf import PptToPdfConverter
from backend.converters.ppt_to_image import PptToImageConverter
from backend.converters.ppt_to_image_wps import PptToImageWpsConverter
from backend.converters.ppt_to_video import PptToVideoConverter
from backend.converters.ppt_to_video_wps import PptToVideoWpsConverter
from backend.converters.ppt_to_video_smart import PptToVideoSmartConverter
from backend.converters.ppt_to_video_pptx2mp4 import PptToVideoPptx2mp4Converter
from backend.converters.json_to_xlsx import JsonToXlsxConverter
from backend.converters.excel_to_image import ExcelToImageConverter
from backend.converters.excel_to_html import ExcelToHtmlConverter
# from backend.converters.pdf_to_psd import PdfToPsdConverter  # 已移除：缺少psd_tools依赖

# 配置常量（后续可移至 config.py）
import sys

# 判断是否在打包环境中
if getattr(sys, 'frozen', False):
    # 打包后，使用用户目录
    import tempfile
    base_dir = os.path.join(tempfile.gettempdir(), 'doc-converter')
    default_upload_dir = os.path.join(base_dir, 'uploads')
    default_download_dir = os.path.join(base_dir, 'downloads')
else:
    # 开发环境，使用项目目录
    default_upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
    default_download_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "downloads"))

UPLOAD_DIR = os.path.abspath(os.environ.get("BACKEND_UPLOAD_DIR", default_upload_dir))
DOWNLOAD_DIR = os.path.abspath(os.environ.get("BACKEND_DOWNLOAD_DIR", default_download_dir))

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class ConverterService:
    """转换服务编排层"""
    
    def __init__(self):
        is_windows = platform.system() == "Windows"
        # 注册所有转换器
        # key: (source_format, target_format)
        self.converters = {
            # JSON 转换
            ('json', 'yaml'): JsonToYamlConverter(),
            ('json', 'yml'): JsonToYamlConverter(),
            ('json', 'xml'): JsonToXmlConverter(),
            ('json', 'csv'): JsonToCsvConverter(),
            ('json', 'html'): JsonToHtmlConverter(),
            ('json', 'pdf'): JsonToPdfConverter(),
            ('json', 'base64'): JsonToBase64Converter(),
            ('json', 'png'): JsonToImageConverter(),
            ('json', 'jpg'): JsonToImageConverter(),
            ('json', 'jpeg'): JsonToImageConverter(),
            ('json', 'svg'): JsonToSvgConverter(),
            ('json', 'xlsx'): JsonToXlsxConverter(),
            # XML 转换
            ('xml', 'json'): XmlToJsonConverter(),
            ('xml', 'yaml'): XmlToYamlConverter(),
            ('xml', 'yml'): XmlToYamlConverter(),
            ('xml', 'csv'): XmlToCsvConverter(),
            ('xml', 'html'): XmlToHtmlConverter(),
            ('xml', 'txt'): XmlToTxtConverter(),
            ('xml', 'pdf'): XmlToPdfConverter(),
            ('xml', 'xlsx'): XmlToXlsxConverter(),
            ('xml', 'png'): XmlToImageConverter(),
            ('xml', 'jpg'): XmlToImageConverter(),
            ('xml', 'jpeg'): XmlToImageConverter(),
            ('xml', 'svg'): XmlToSvgConverter(),
            # DOCX 转换
            ('docx', 'txt'): DocxToTxtConverter(),
            ('docx', 'pdf'): DocxToPdfConverter(),
            ('docx', 'png'): DocxToImageConverter(),
            ('docx', 'jpg'): DocxToImageConverter(),
            ('docx', 'jpeg'): DocxToImageConverter(),
            ('docx', 'epub'): DocxToEpubConverter(),
            ('docx', 'xlsx'): DocxToExcelConverter(),
            ('docx', 'xls'): DocxToExcelConverter(),
            ('docx', 'pptx'): DocxToPptConverter(),
            ('docx', 'ppt'): DocxToPptConverter(),
            # HTML 转换
            ('html', 'pdf'): HtmlToPdfConverter(),
            ('html', 'txt'): HtmlToTxtConverter(),
            ('html', 'text'): HtmlToTxtConverter(),
            ('html', 'md'): HtmlToMarkdownConverter(),
            ('html', 'markdown'): HtmlToMarkdownConverter(),
            ('html', 'png'): HtmlToImageConverter(),
            ('html', 'jpg'): HtmlToImageConverter(),
            ('html', 'jpeg'): HtmlToImageConverter(),
            ('html', 'docx'): HtmlToDocxConverter(),
            ('html', 'doc'): HtmlToDocxConverter(),
            ('html', 'json'): HtmlToJsonConverter(),
            ('html', 'gif'): HtmlToGifConverter(),
            ('html', 'svg'): HtmlToSvgConverter(),
            # PDF 转换
            ('pdf', 'txt'): PdfToTxtConverter(),
            ('pdf', 'docx'): PdfToDocxConverter(),
            ('pdf', 'doc'): PdfToDocxConverter(),
            ('pdf', 'html'): PdfToHtmlConverter(),
            ('pdf', 'png'): PdfToImageConverter(),
            ('pdf', 'jpg'): PdfToImageConverter(),
            ('pdf', 'jpeg'): PdfToImageConverter(),
            ('pdf', 'bmp'): PdfToImageConverter(),
            ('pdf', 'tiff'): PdfToImageConverter(),
            ('pdf', 'json'): PdfToJsonConverter(),
            ('pdf', 'base64'): PdfToBase64Converter(),
            ('pdf', 'md'): PdfToMdConverter(),
            ('pdf', 'svg'): PdfToSvgConverter(),
            ('pdf', 'epub'): PdfToEpubConverter(),
            ('pdf', 'gif'): PdfToGifConverter(),
            ('pdf', 'webp'): PdfToWebpConverter(),
            ('pdf', 'pptx'): PdfToPptConverter(),
            ('pdf', 'ppt'): PdfToPptConverter(),
            ('pdf', 'rtf'): PdfToRtfConverter(),
            ('pdf', 'xlsx'): PdfToExcelConverter(),
            ('pdf', 'xls'): PdfToExcelConverter(),
            # ('pdf', 'psd'): PdfToPsdConverter(),  # 已移除：缺少psd_tools依赖
            # PPT 转换
            ('pptx', 'pdf'): PptToPdfConverter(),
            ('ppt', 'pdf'): PptToPdfConverter(),
            ('pptx', 'png'): PptToImageWpsConverter(),  # 使用WPS导出PNG
            ('ppt', 'png'): PptToImageWpsConverter(),  # 使用WPS导出PNG
            ('pptx', 'jpg'): PptToImageWpsConverter(),  # 使用WPS导出JPG
            ('ppt', 'jpg'): PptToImageWpsConverter(),  # 使用WPS导出JPG
            ('pptx', 'jpeg'): PptToImageWpsConverter(),  # 使用WPS导出JPEG
            ('ppt', 'jpeg'): PptToImageWpsConverter(),  # 使用WPS导出JPEG
            ('pptx', 'mp4'): PptToVideoSmartConverter(),  # 智能转换器（WPS修复版）
            ('ppt', 'mp4'): PptToVideoSmartConverter(),  # 智能转换器（WPS修复版）
            # EXCEL 转换
            ('xlsx', 'pdf'): ExcelToPdfConverter(),
            ('xls', 'pdf'): ExcelToPdfConverter(),
            ('xlsx', 'pptx'): ExcelToPptConverter(),
            ('xls', 'pptx'): ExcelToPptConverter(),
            ('xlsx', 'ppt'): ExcelToPptConverter(),
            ('xls', 'ppt'): ExcelToPptConverter(),
            ('xlsx', 'png'): ExcelToImageConverter(),
            ('xls', 'png'): ExcelToImageConverter(),
            ('xlsx', 'jpg'): ExcelToImageConverter(),
            ('xls', 'jpg'): ExcelToImageConverter(),
            ('xlsx', 'jpeg'): ExcelToImageConverter(),
            ('xls', 'jpeg'): ExcelToImageConverter(),
            ('xlsx', 'html'): ExcelToHtmlConverter(),
            ('xls', 'html'): ExcelToHtmlConverter(),
            # TXT 转换
            ('txt', 'pdf'): TxtToPdfConverter(),
            ('txt', 'html'): TxtToHtmlConverter(),
            ('txt', 'png'): TxtToImageConverter(),
            ('txt', 'jpg'): TxtToImageConverter(),
            ('txt', 'jpeg'): TxtToImageConverter(),
            ('txt', 'mp3'): TxtToSpeechConverter(),
            ('txt', 'wav'): TxtToSpeechConverter(),
            ('txt', 'ascii'): TxtToAsciiConverter(),
            ('txt', 'binary'): TxtToBinaryConverter(),
            ('txt', 'bin'): TxtToBinaryConverter(),
            ('txt', 'csv'): TxtToCsvConverter(),
            ('txt', 'hex'): TxtToHexConverter(),
        }

        if not is_windows:
            self.converters[('pptx', 'png')] = PptToImageConverter()
            self.converters[('ppt', 'png')] = PptToImageConverter()
            self.converters[('pptx', 'jpg')] = PptToImageConverter()
            self.converters[('ppt', 'jpg')] = PptToImageConverter()
            self.converters[('pptx', 'jpeg')] = PptToImageConverter()
            self.converters[('ppt', 'jpeg')] = PptToImageConverter()
            self.converters[('pptx', 'mp4')] = PptToVideoPptx2mp4Converter()
    
    def convert_file(self, input_path: str, target_format: str, original_filename: str = None, **options) -> Dict[str, Any]:
        """
        统一转换入口
        """
        source_format = input_path.split('.')[-1].lower()
        target_format = target_format.lower()
        
        converter_key = (source_format, target_format)
        if converter_key not in self.converters:
            raise ValueError(f"Unsupported conversion: {source_format} to {target_format}")
        
        converter = self.converters[converter_key]
        print(f"[ConverterService] 使用转换器: {type(converter).__name__}")
        
        # 生成输出路径，使用优化的文件名策略
        if original_filename:
            # 清理文件名 (移除路径/非法字符)
            safe_filename = FileHandler.sanitize_filename(original_filename)
            
            # 移除原始扩展名，保留文件名
            base_name = os.path.splitext(safe_filename)[0]
            display_name = f"{base_name}.{target_format}"
            
            # 生成短哈希（6位）确保唯一性
            short_hash = str(uuid.uuid4())[:8]
            storage_filename = f"{base_name}_{short_hash}.{target_format}"
            output_path = os.path.join(DOWNLOAD_DIR, storage_filename)
            
            # 如果文件已存在（极小概率），添加数字后缀
            counter = 1
            while os.path.exists(output_path):
                storage_filename = f"{base_name}_{short_hash}_{counter}.{target_format}"
                output_path = os.path.join(DOWNLOAD_DIR, storage_filename)
                counter += 1
        else:
            unique_id = str(uuid.uuid4())
            display_name = f"converted.{target_format}"
            storage_filename = f"{unique_id}.{target_format}"
            output_path = os.path.join(DOWNLOAD_DIR, storage_filename)
        
        # 调用具体转换器
        result = converter.convert(input_path, output_path, **options)
        
        # 检查实际输出文件（可能是 ZIP）
        actual_output_path = result.get('output_path', output_path)
        actual_storage_filename = os.path.basename(actual_output_path)
        
        # 如果是 ZIP 文件，也需要处理显示名称
        if actual_storage_filename.endswith('.zip'):
            # 提取原始基础名，移除哈希部分
            if original_filename:
                actual_display_name = f"{base_name}.zip"
            else:
                actual_display_name = "converted.zip"
        else:
            actual_display_name = display_name
        
        # 补充返回信息
        print(f"[ConverterService] Expected output: {output_path}")
        print(f"[ConverterService] Actual output: {actual_output_path}")
        print(f"[ConverterService] Storage filename: {actual_storage_filename}")
        print(f"[ConverterService] Display filename: {actual_display_name}")
        print(f"[ConverterService] File exists: {os.path.exists(actual_output_path)}")
        
        result.update({
            'filename': actual_storage_filename,  # 后端存储的实际文件名
            'display_name': actual_display_name,  # 用户看到的文件名
            'download_url': f"/downloads/{actual_storage_filename}"
        })
        
        return result

    def get_supported_conversions(self) -> List[Dict[str, str]]:
        """获取支持的转换列表"""
        return [
            {'source': src, 'target': tgt} 
            for src, tgt in self.converters.keys()
        ]
