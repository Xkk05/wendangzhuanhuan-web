#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OCR转换服务 - 协调OCR识别和文档生成
需求: 2.4, 5.1, 5.2, 5.3, 5.4, 5.5, 8.1, 8.4, 10.1, 10.2, 10.3, 10.4, 10.5
"""

import os
import tempfile
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

import pypdf

from .ocr_service import BaiduOCRService
from conversion_core.services.retry_strategy import ErrorCode
from conversion_core.services.pdf_validator import PDFValidator, validate_pdf_file, ValidationResult


# 大文件处理阈值
MAX_FILE_SIZE_MB = 50  # 50MB
MAX_PAGES_PER_CHUNK = 10  # 每块最多10页


@dataclass
class OCRConfig:
    """OCR配置模型"""
    api_key: str                    # API密钥
    model: str = "auto"             # 模型选择 (auto/deepseek-ocr/paddleocr-vl/pp-structurev3)
    has_seal: bool = False          # 印章识别
    has_formula: bool = False       # 公式识别
    has_chart: bool = False         # 图表识别
    target_format: str = "word"     # 目标格式 (word/excel)
    output_dir: str = ""            # 输出目录


@dataclass
class OCRPageResult:
    """OCR页面结果模型"""
    page_number: int                # 页码
    markdown_text: str              # Markdown文本
    tables: List[Dict]              # 表格数据
    images: List[Dict]              # 图片数据
    success: bool                   # 是否成功
    error: Optional[str] = None     # 错误信息
    seals: List[Dict] = None        # 印章区域数据
    
    def __post_init__(self):
        if self.seals is None:
            self.seals = []


def calculate_progress(current_page: int, total_pages: int) -> float:
    """
    计算进度百分比
    
    属性10: 进度百分比计算正确性
    对于任意总页数N和当前页码P，进度百分比应当等于(P/N)*100
    验证: 需求 5.2, 5.3
    
    Args:
        current_page: 当前页码 (1-based)
        total_pages: 总页数
        
    Returns:
        float: 进度百分比 (0-100)
    """
    if total_pages <= 0:
        return 0.0
    if current_page <= 0:
        return 0.0
    if current_page > total_pages:
        current_page = total_pages
    return (current_page / total_pages) * 100


class OCRConversionService:
    """OCR转换服务 - 协调OCR识别和文档生成"""
    
    # 模型名称映射
    MODEL_MAPPING = {
        "deepseek-ocr": "deepseek-ocr",
        "paddleocr-vl": "paddleocr-vl-0.9b",
        "pp-structurev3": "pp-structurev3"
    }
    
    def __init__(self, api_key: str, config: Dict):
        """
        初始化OCR转换服务
        
        Args:
            api_key: 百度千帆API密钥
            config: 转换配置
                - model: 模型选择 (auto/deepseek-ocr/paddleocr-vl/pp-structurev3)
                - has_seal: 是否包含印章
                - has_formula: 是否包含公式
                - has_chart: 是否包含图表
                - target_format: 目标格式 (word/excel)
                - output_dir: 输出目录
        """
        self.api_key = api_key
        self.config = OCRConfig(
            api_key=api_key,
            model=config.get("model", "auto"),
            has_seal=config.get("has_seal", False),
            has_formula=config.get("has_formula", False),
            has_chart=config.get("has_chart", False),
            target_format=config.get("target_format", "word"),
            output_dir=config.get("output_dir", "")
        )
        self.ocr_service = BaiduOCRService(api_key)

    def convert(self, file_path: str, progress_callback: Optional[Callable] = None) -> Dict:
        """
        执行OCR转换
        
        支持大文件分块处理 (>50MB或>10页) - 需求 2.4, 8.1, 8.4
        
        Args:
            file_path: PDF文件路径
            progress_callback: 进度回调函数 (current_page, total_pages, message)
            
        Returns:
            dict: {success: bool, output_file: str, error: str, error_code: str, pages: list}
        """
        print(f"[OCR转换服务] 开始处理文件: {file_path}")
        try:
            # 使用PDF验证器验证文件 (需求 2.2, 2.4)
            validation_result = validate_pdf_file(file_path)
            
            if not validation_result.valid:
                return {
                    "success": False,
                    "error": validation_result.error,
                    "error_code": ErrorCode.FILE_ERROR.value,
                    "output_file": None
                }
            
            # 获取文件大小
            file_size_mb = validation_result.file_size_mb
            
            # 获取PDF页数
            try:
                reader = pypdf.PdfReader(file_path)
                total_pages = len(reader.pages)
            except pypdf.errors.PdfReadError as e:
                return {
                    "success": False,
                    "error": f"PDF文件已损坏或无法读取: {str(e)}",
                    "error_code": ErrorCode.FILE_ERROR.value,
                    "output_file": None
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"无法读取PDF文件: {str(e)}",
                    "error_code": ErrorCode.FILE_ERROR.value,
                    "output_file": None
                }
            
            # 选择OCR模型
            selected_model = self._select_model(self.config)
            print(f"[OCR转换服务] 选择模型: {selected_model}, 总页数: {total_pages}, 文件大小: {file_size_mb:.2f}MB")
            
            # 判断是否需要分块处理 (需求 2.4)
            needs_chunking = file_size_mb > MAX_FILE_SIZE_MB or total_pages > MAX_PAGES_PER_CHUNK
            print(f"[OCR转换服务] 是否分块处理: {needs_chunking}")
            
            # 发送初始进度
            if progress_callback:
                if needs_chunking:
                    progress_callback(0, total_pages, f"文件较大，正在分块处理... 使用模型: {selected_model}")
                else:
                    progress_callback(0, total_pages, f"开始OCR转换，使用模型: {selected_model}")
            
            # 处理每一页 (需求 8.1 - 按顺序处理)
            if needs_chunking:
                page_results = self._process_pages_chunked(file_path, total_pages, selected_model, progress_callback)
            else:
                page_results = self._process_pages(file_path, total_pages, selected_model, progress_callback)
            
            successful_pages = [p for p in page_results if p.success]
            failed_pages = [p for p in page_results if not p.success]
            
            # 检查是否有认证错误（需要立即停止）
            auth_errors = [p for p in page_results if p.error and ErrorCode.AUTH_ERROR.value in str(p.error)]
            if auth_errors:
                if progress_callback:
                    progress_callback(0, total_pages, "API密钥无效，请检查配置")
                return {
                    "success": False,
                    "error": "API密钥无效，请检查配置",
                    "error_code": ErrorCode.AUTH_ERROR.value,
                    "output_file": None,
                    "pages": [{"page": p.page_number, "error": p.error} for p in page_results]
                }
            
            if not page_results:
                if progress_callback:
                    progress_callback(0, total_pages, "没有获得任何OCR页面结果")
                return {
                    "success": False,
                    "error": "没有获得任何OCR页面结果",
                    "error_code": ErrorCode.OCR_ERROR.value,
                    "output_file": None,
                    "pages": []
                }

            if not successful_pages:
                first_error = page_results[0].error if page_results else "未知错误"
                if progress_callback:
                    progress_callback(0, total_pages, f"所有页面OCR识别失败: {first_error}")
                return {
                    "success": False,
                    "error": f"所有页面OCR识别失败: {first_error}",
                    "error_code": ErrorCode.OCR_ERROR.value,
                    "output_file": None,
                    "pages": [{"page": p.page_number, "error": p.error} for p in page_results]
                }

            partial_failed = bool(failed_pages)

            if progress_callback:
                if partial_failed:
                    progress_callback(total_pages, total_pages, "OCR识别完成（部分页面失败）")
                else:
                    progress_callback(total_pages, total_pages, "OCR识别完成")
            
            return {
                "success": True,
                "output_file": None,
                "error": None,
                "error_code": None,
                "pages": page_results,
                "model": selected_model,
                "total_pages": total_pages,
                "successful_pages": len(successful_pages),
                "failed_pages": [{"page": p.page_number, "error": p.error} for p in failed_pages],
                "partial_failed": partial_failed,
                "chunked": needs_chunking
            }
            
        except Exception as e:
            if progress_callback:
                progress_callback(0, 0, f"OCR转换失败: {str(e)}")
            return {
                "success": False,
                "error": f"OCR转换失败: {str(e)}",
                "error_code": ErrorCode.OCR_ERROR.value,
                "output_file": None
            }

    def _select_model(self, config: OCRConfig) -> str:
        """
        根据配置选择OCR模型
        
        Args:
            config: OCR配置
            
        Returns:
            str: 选择的模型名称
        """
        # 如果用户手动指定了模型（非auto），直接使用
        if config.model != "auto":
            return self.MODEL_MAPPING.get(config.model, config.model)
        
        # 自动选择模型逻辑
        # 优先级: 印章/公式 > 图表 > 默认
        
        # 如果包含印章或公式，使用PP-StructureV3
        if config.has_seal or config.has_formula:
            return "pp-structurev3"
        
        # 如果包含图表，使用PaddleOCR-VL
        if config.has_chart:
            return "paddleocr-vl-0.9b"
        
        # 默认使用DeepSeek-OCR（快速处理）
        return "deepseek-ocr"
    
    def _process_pages(self, file_path: str, total_pages: int, 
                       model: str, progress_callback: Optional[Callable] = None) -> List[OCRPageResult]:
        """
        处理PDF每一页，返回OCR结果列表
        
        属性13: 多页处理顺序保持
        对于任意多页PDF，处理结果列表的顺序应当与原PDF页码顺序一致
        验证: 需求 8.1
        
        Args:
            file_path: PDF文件路径
            total_pages: 总页数
            model: 使用的OCR模型
            progress_callback: 进度回调函数
            
        Returns:
            list: OCRPageResult列表 (按页码顺序)
        """
        results = []
        
        # 按顺序处理每一页 (需求 8.1)
        for page_num in range(1, total_pages + 1):
            # 计算并发送进度更新 (需求 5.2, 5.3) - 开始处理该页
            if progress_callback:
                progress = calculate_progress(page_num - 1, total_pages)  # 使用page_num-1表示该页尚未完成
                progress_callback(page_num - 1, total_pages, f"正在识别第{page_num}/{total_pages}页...")
            
            try:
                # 调用OCR服务
                ocr_result = self._ocr_single_page(file_path, page_num, model)
                
                if ocr_result.get("success"):
                    page_result = OCRPageResult(
                        page_number=page_num,
                        markdown_text=ocr_result.get("text", ""),
                        tables=ocr_result.get("tables", []),
                        images=ocr_result.get("images", []),
                        success=True,
                        error=None,
                        seals=ocr_result.get("seals", [])
                    )
                    # 该页处理成功，发送进度更新
                    if progress_callback:
                        progress = calculate_progress(page_num, total_pages)
                        progress_callback(page_num, total_pages, f"第{page_num}页识别完成 ({progress:.0f}%)")
                else:
                    # 需求 8.4: 某页OCR识别失败，记录错误并继续处理剩余页面
                    page_result = OCRPageResult(
                        page_number=page_num,
                        markdown_text="",
                        tables=[],
                        images=[],
                        success=False,
                        error=ocr_result.get("error", "未知错误")
                    )
                    # 该页处理失败，也发送进度更新
                    if progress_callback:
                        progress = calculate_progress(page_num, total_pages)
                        progress_callback(page_num, total_pages, f"第{page_num}页识别失败: {ocr_result.get('error', '未知错误')}")
                    
            except AuthenticationError as e:
                # 认证错误，停止处理并返回错误
                page_result = OCRPageResult(
                    page_number=page_num,
                    markdown_text="",
                    tables=[],
                    images=[],
                    success=False,
                    error=f"{ErrorCode.AUTH_ERROR.value}: {str(e)}"
                )
                results.append(page_result)
                if progress_callback:
                    progress_callback(page_num, total_pages, f"认证失败: {str(e)}")
                # 不继续处理其他页面
                break
                    
            except Exception as e:
                # 其他错误，记录并继续处理下一页（需求8.4）
                page_result = OCRPageResult(
                    page_number=page_num,
                    markdown_text="",
                    tables=[],
                    images=[],
                    success=False,
                    error=str(e)
                )
                if progress_callback:
                    progress = calculate_progress(page_num, total_pages)
                    progress_callback(page_num, total_pages, f"第{page_num}页处理异常: {str(e)}")
            
            results.append(page_result)
        
        return results
    
    def _process_pages_chunked(self, file_path: str, total_pages: int,
                               model: str, progress_callback: Optional[Callable] = None) -> List[OCRPageResult]:
        """
        分块处理大文件PDF (>50MB或>10页)
        
        需求 2.4: 若PDF文件超过50MB或10页，则OCR系统应当将文件拆分为较小的块进行处理
        属性13: 多页处理顺序保持
        
        Args:
            file_path: PDF文件路径
            total_pages: 总页数
            model: 使用的OCR模型
            progress_callback: 进度回调函数
            
        Returns:
            list: OCRPageResult列表 (按页码顺序)
        """
        results = []
        
        # 计算分块
        chunks = []
        for start_page in range(1, total_pages + 1, MAX_PAGES_PER_CHUNK):
            end_page = min(start_page + MAX_PAGES_PER_CHUNK - 1, total_pages)
            chunks.append((start_page, end_page))
        
        total_chunks = len(chunks)
        
        # 按顺序处理每个分块
        for chunk_idx, (start_page, end_page) in enumerate(chunks):
            chunk_num = chunk_idx + 1
            
            if progress_callback:
                progress_callback(start_page - 1, total_pages, 
                                f"正在处理第{chunk_num}/{total_chunks}块 (第{start_page}-{end_page}页)...")
            
            # 处理当前分块中的每一页
            for page_num in range(start_page, end_page + 1):
                # 计算并发送进度更新 - 开始处理该页
                if progress_callback:
                    progress = calculate_progress(page_num - 1, total_pages)
                    progress_callback(page_num - 1, total_pages, 
                                    f"正在识别第{page_num}/{total_pages}页 (块{chunk_num}/{total_chunks})...")
                
                try:
                    # 调用OCR服务
                    ocr_result = self._ocr_single_page(file_path, page_num, model)
                    
                    if ocr_result.get("success"):
                        page_result = OCRPageResult(
                            page_number=page_num,
                            markdown_text=ocr_result.get("text", ""),
                            tables=ocr_result.get("tables", []),
                            images=ocr_result.get("images", []),
                            success=True,
                            error=None
                        )
                        # 该页处理成功，发送进度更新
                        if progress_callback:
                            progress = calculate_progress(page_num, total_pages)
                            progress_callback(page_num, total_pages, 
                                            f"第{page_num}页识别完成 (块{chunk_num}/{total_chunks}) ({progress:.0f}%)")
                    else:
                        # 需求 8.4: 某页OCR识别失败，记录错误并继续处理剩余页面
                        page_result = OCRPageResult(
                            page_number=page_num,
                            markdown_text="",
                            tables=[],
                            images=[],
                            success=False,
                            error=ocr_result.get("error", "未知错误")
                        )
                        # 该页处理失败，也发送进度更新
                        if progress_callback:
                            progress = calculate_progress(page_num, total_pages)
                            progress_callback(page_num, total_pages, 
                                            f"第{page_num}页识别失败: {ocr_result.get('error', '未知错误')}")
                        
                except AuthenticationError as e:
                    # 认证错误，停止处理并返回错误
                    page_result = OCRPageResult(
                        page_number=page_num,
                        markdown_text="",
                        tables=[],
                        images=[],
                        success=False,
                        error=f"{ErrorCode.AUTH_ERROR.value}: {str(e)}"
                    )
                    results.append(page_result)
                    if progress_callback:
                        progress_callback(page_num, total_pages, f"认证失败: {str(e)}")
                    # 不继续处理其他页面
                    return results
                        
                except Exception as e:
                    # 其他错误，记录并继续处理下一页（需求8.4）
                    page_result = OCRPageResult(
                        page_number=page_num,
                        markdown_text="",
                        tables=[],
                        images=[],
                        success=False,
                        error=str(e)
                    )
                    if progress_callback:
                        progress = calculate_progress(page_num, total_pages)
                        progress_callback(page_num, total_pages, 
                                        f"第{page_num}页处理异常: {str(e)}")
                
                results.append(page_result)
        
        return results

    def _ocr_single_page(self, file_path: str, page_num: int, model: str) -> Dict:
        """
        对单页进行OCR识别
        
        Args:
            file_path: PDF文件路径
            page_num: 页码（从1开始）
            model: OCR模型
            
        Returns:
            dict: OCR结果
        """
        print(f"[OCR单页处理] 开始处理第{page_num}页, 模型: {model}")
        try:
            # 对于支持PDF的模型，可以直接处理整个文件
            # 对于DeepSeek-OCR，需要先将PDF页面转为图片
            
            if model == "deepseek-ocr":
                # DeepSeek-OCR需要图片输入，先转换PDF页面为图片
                image_path = self._pdf_page_to_image(file_path, page_num)
                if not image_path:
                    return {
                        "success": False, 
                        "error": "PDF页面转图片失败",
                        "error_code": ErrorCode.FILE_ERROR.value
                    }
                
                try:
                    result = self.ocr_service.ocr_with_deepseek(
                        image_path,
                        prompt="Convert the document to markdown."
                    )
                finally:
                    # 清理临时图片文件
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        
            elif model == "paddleocr-vl-0.9b":
                # PaddleOCR-VL支持PDF，但需要按页处理
                # 先提取单页PDF
                single_page_pdf = self._extract_single_page(file_path, page_num)
                if not single_page_pdf:
                    return {
                        "success": False, 
                        "error": "提取PDF页面失败",
                        "error_code": ErrorCode.FILE_ERROR.value
                    }
                
                try:
                    result = self.ocr_service.ocr_with_paddleocr_vl(
                        single_page_pdf,
                        use_layout=True,
                        use_chart=self.config.has_chart
                    )
                finally:
                    # 清理临时文件
                    if os.path.exists(single_page_pdf):
                        os.remove(single_page_pdf)
                        
            elif model == "pp-structurev3":
                # PP-StructureV3支持PDF
                single_page_pdf = self._extract_single_page(file_path, page_num)
                if not single_page_pdf:
                    return {
                        "success": False, 
                        "error": "提取PDF页面失败",
                        "error_code": ErrorCode.FILE_ERROR.value
                    }
                
                try:
                    result = self.ocr_service.ocr_with_pp_structure(
                        single_page_pdf,
                        use_seal=self.config.has_seal,
                        use_formula=self.config.has_formula,
                        use_chart=self.config.has_chart
                    )
                finally:
                    # 清理临时文件
                    if os.path.exists(single_page_pdf):
                        os.remove(single_page_pdf)
            else:
                return {
                    "success": False, 
                    "error": f"不支持的模型: {model}",
                    "error_code": ErrorCode.OCR_ERROR.value
                }
            
            # 检查结果中是否有认证错误，如果有则需要停止处理
            if not result.get("success") and result.get("error_code") == ErrorCode.AUTH_ERROR.value:
                # 认证错误不应继续处理其他页面
                raise AuthenticationError(result.get("error", "API密钥无效"))
            
            return result
            
        except AuthenticationError:
            # 重新抛出认证错误
            raise
        except Exception as e:
            return {
                "success": False, 
                "error": str(e),
                "error_code": ErrorCode.OCR_ERROR.value
            }


    def _pdf_page_to_image(self, file_path: str, page_num: int) -> Optional[str]:
        """
        将PDF页面转换为图片
        
        Args:
            file_path: PDF文件路径
            page_num: 页码（从1开始）
            
        Returns:
            str: 临时图片文件路径，失败返回None
        """
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(file_path)
            page = doc[page_num - 1]
            
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_file.close()
            pix.save(temp_file.name)
            
            doc.close()
            return temp_file.name
            
        except ImportError:
            try:
                from pdf2image import convert_from_path
                
                images = convert_from_path(
                    file_path,
                    first_page=page_num,
                    last_page=page_num,
                    dpi=144
                )
                
                if images:
                    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    images[0].save(temp_file.name, 'PNG')
                    return temp_file.name
                    
            except ImportError as e:
                print(f"[OCR转换服务] pdf2image不可用: {e}")
                
        except Exception as e:
            print(f"[OCR转换服务] 将PDF页面转换为图片失败: file={file_path}, page={page_num}, error={e}")
        
        return None
    
    def _extract_single_page(self, file_path: str, page_num: int) -> Optional[str]:
        """
        从PDF中提取单页
        
        Args:
            file_path: PDF文件路径
            page_num: 页码（从1开始）
            
        Returns:
            str: 临时PDF文件路径，失败返回None
        """
        try:
            reader = pypdf.PdfReader(file_path)
            writer = pypdf.PdfWriter()
            
            # 添加指定页面（pypdf使用0索引）
            writer.add_page(reader.pages[page_num - 1])
            
            # 保存为临时文件
            temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            with open(temp_file.name, 'wb') as f:
                writer.write(f)
            
            return temp_file.name
            
        except Exception:
            return None


class AuthenticationError(Exception):
    """认证错误异常"""
    pass
