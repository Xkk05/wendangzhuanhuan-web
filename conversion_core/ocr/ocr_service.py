#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
百度千帆OCR服务集成
参考: docs/百度千帆OCR接入文档.md
需求: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import requests
import base64
import os
import time
from typing import Dict, Literal, Optional, List

from conversion_core.services.retry_strategy import (
    RetryStrategy, 
    ErrorCode, 
    OCRError,
    classify_http_error,
    create_ocr_error_from_response,
    create_file_error,
    create_network_error,
    create_timeout_error
)


class BaiduOCRService:
    """百度千帆OCR服务类"""
    
    def __init__(self, api_key: str):
        """
        初始化OCR服务
        
        Args:
            api_key: 百度千帆API Key (格式: bce-v3/ALTAK-xxx)
        """
        self.api_key = api_key
        self.base_url = "https://qianfan.baidubce.com"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def select_model(self, file_type: str = 'document', 
                    has_seal: bool = False, 
                    has_formula: bool = False,
                    has_chart: bool = False) -> str:
        """
        智能选择OCR模型
        
        Args:
            file_type: 文件类型 (document/chart/contract)
            has_seal: 是否包含印章
            has_formula: 是否包含公式
            has_chart: 是否包含图表
            
        Returns:
            str: 模型名称
        """
        # 如果是合同、发票等专业文档
        if has_seal or has_formula:
            return "pp-structurev3"
        # 如果包含图表
        elif has_chart or file_type == 'chart':
            return "paddleocr-vl-0.9b"
        # 默认快速OCR
        else:
            return "deepseek-ocr"
    
    def ocr_with_deepseek(self, image_path: str, 
                         prompt: str = "OCR this image.",
                         max_tokens: int = 4096) -> Dict:
        """
        DeepSeek-OCR调用 - 通用文档识别
        
        Args:
            image_path: 图片路径
            prompt: OCR提示词
                - "OCR this image." - 普通OCR
                - "Convert the document to markdown." - 转Markdown
                - "Free OCR." - 纯文本提取
                - "Parse the figure." - 图表解析
            max_tokens: 最大输出token数
            
        Returns:
            dict: OCR结果
        """
        # 验证文件存在
        if not os.path.exists(image_path):
            return {
                'success': False,
                'error': f'文件不存在: {image_path}',
                'error_code': ErrorCode.FILE_ERROR.value
            }
        
        try:
            # 读取图片并转Base64
            with open(image_path, "rb") as f:
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
        except IOError as e:
            return {
                'success': False,
                'error': f'文件读取失败: {str(e)}',
                'error_code': ErrorCode.FILE_ERROR.value
            }
        
        # 构建请求
        payload = {
            "model": "deepseek-ocr",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_data}"
                        }
                    }
                ]
            }],
            "stream": False,
            "max_tokens": max_tokens
        }
        
        # 带重试的请求
        return self._execute_with_retry(
            url=f"{self.base_url}/v2/chat/completions",
            payload=payload,
            model='deepseek-ocr',
            timeout=60
        )
    
    def ocr_with_paddleocr_vl(self, file_path: str,
                             use_layout: bool = True,
                             use_chart: bool = False,
                             use_doc_orient: bool = False,
                             use_unwarp: bool = False,
                             visualize: bool = True) -> Dict:
        """
        PaddleOCR-VL调用 - 多模态OCR，支持版面分析
        
        Args:
            file_path: 文件路径（图片或PDF）
            use_layout: 启用版面分析
            use_chart: 启用图表识别
            use_doc_orient: 启用文档方向矫正
            use_unwarp: 启用扭曲矫正
            visualize: 返回可视化结果图
            
        Returns:
            dict: OCR结果
        """
        # 验证文件存在（非URL情况）
        if not file_path.startswith('http') and not os.path.exists(file_path):
            return {
                'success': False,
                'error': f'文件不存在: {file_path}',
                'error_code': ErrorCode.FILE_ERROR.value
            }
        
        # 判断文件类型
        ext = os.path.splitext(file_path)[1].lower()
        file_type = 0 if ext == '.pdf' else 1
        
        # 读取文件并转Base64（或使用URL）
        if file_path.startswith('http'):
            file_value = file_path
        else:
            try:
                with open(file_path, "rb") as f:
                    file_value = base64.b64encode(f.read()).decode('utf-8')
            except IOError as e:
                return {
                    'success': False,
                    'error': f'文件读取失败: {str(e)}',
                    'error_code': ErrorCode.FILE_ERROR.value
                }
        
        payload = {
            "model": "paddleocr-vl-0.9b",
            "file": file_value,
            "fileType": file_type,
            "useLayoutDetection": use_layout,
            "useDocOrientationClassify": use_doc_orient,
            "useDocUnwarping": use_unwarp,
            "useChartRecognition": use_chart,
            "visualize": visualize,
            "temperature": 0.0,
            "topP": 1.0,
            "repetitionPenalty": 1.0,
            "minPixels": 147384,
            "maxPixels": 2822400
        }
        
        # 带重试的请求
        return self._execute_with_retry(
            url=f"{self.base_url}/v2/ocr/paddleocr",
            payload=payload,
            model='paddleocr-vl-0.9b',
            timeout=120,
            result_parser=self._parse_paddleocr_result
        )
    
    def ocr_with_pp_structure(self, file_path: str,
                             use_seal: bool = False,
                             use_table: bool = True,
                             use_formula: bool = True,
                             use_chart: bool = False,
                             visualize: bool = True) -> Dict:
        """
        PP-StructureV3调用 - 文档结构理解，支持印章/表格/公式
        
        Args:
            file_path: 文件路径（图片或PDF）
            use_seal: 启用印章识别
            use_table: 启用表格识别
            use_formula: 启用公式识别
            use_chart: 启用图表识别
            visualize: 返回可视化结果图
            
        Returns:
            dict: OCR结果
        """
        # 验证文件存在（非URL情况）
        if not file_path.startswith('http') and not os.path.exists(file_path):
            return {
                'success': False,
                'error': f'文件不存在: {file_path}',
                'error_code': ErrorCode.FILE_ERROR.value
            }
        
        # 判断文件类型
        ext = os.path.splitext(file_path)[1].lower()
        file_type = 0 if ext == '.pdf' else 1
        
        # 读取文件并转Base64
        if file_path.startswith('http'):
            file_value = file_path
        else:
            try:
                with open(file_path, "rb") as f:
                    file_value = base64.b64encode(f.read()).decode('utf-8')
            except IOError as e:
                return {
                    'success': False,
                    'error': f'文件读取失败: {str(e)}',
                    'error_code': ErrorCode.FILE_ERROR.value
                }
        
        payload = {
            "model": "pp-structurev3",
            "file": file_value,
            "fileType": file_type,
            "useSealRecognition": use_seal,
            "useTableRecognition": use_table,
            "useFormulaRecognition": use_formula,
            "useChartRecognition": use_chart,
            "useRegionDetection": True,
            "visualize": visualize,
            # 阈值参数
            "textDetThresh": 0.3,
            "textDetBoxThresh": 0.6,
            "sealDetThresh": 0.2 if use_seal else 0.5,
            "sealDetBoxThresh": 0.6,
            "layoutThreshold": 0.5
        }
        
        # 带重试的请求
        return self._execute_with_retry(
            url=f"{self.base_url}/v2/ocr/paddleocr",
            payload=payload,
            model='pp-structurev3',
            timeout=120,
            result_parser=lambda r, m: self._parse_pp_structure_result(r, m, use_seal, use_table, use_formula)
        )
    
    def _execute_with_retry(self, url: str, payload: Dict, model: str, 
                            timeout: int = 60, 
                            result_parser: Optional[callable] = None) -> Dict:
        """
        带重试机制的HTTP请求执行
        
        Args:
            url: 请求URL
            payload: 请求体
            model: 模型名称
            timeout: 超时时间
            result_parser: 结果解析函数
            
        Returns:
            dict: OCR结果
        """
        last_error = None
        print(f"[OCR API调用] 模型: {model}, URL: {url}, 超时: {timeout}秒")
        
        for attempt in range(RetryStrategy.MAX_RETRIES + 1):
            try:
                print(f"[OCR API调用] 尝试 {attempt + 1}/{RetryStrategy.MAX_RETRIES + 1}")
                response = self.session.post(url, json=payload, timeout=timeout)
                print(f"[OCR API调用] 响应状态码: {response.status_code}")
                
                # 检查HTTP状态码
                if response.status_code != 200:
                    error_code = classify_http_error(response.status_code)
                    error_msg = self._get_error_message(error_code, response)
                    
                    # 判断是否可重试
                    if RetryStrategy.should_retry(error_code, attempt):
                        delay = RetryStrategy.exponential_backoff(attempt)
                        time.sleep(delay)
                        continue
                    
                    return {
                        'success': False,
                        'error': error_msg,
                        'error_code': error_code.value
                    }
                
                result = response.json()
                
                # 使用自定义解析器或默认解析
                if result_parser:
                    return result_parser(result, model)
                else:
                    return self._parse_default_result(result, model)
                    
            except requests.exceptions.Timeout as e:
                last_error = str(e)
                if RetryStrategy.should_retry(ErrorCode.TIMEOUT, attempt):
                    delay = RetryStrategy.exponential_backoff(attempt)
                    time.sleep(delay)
                    continue
                return {
                    'success': False,
                    'error': '网络连接超时，请检查网络',
                    'error_code': ErrorCode.TIMEOUT.value
                }
                
            except requests.exceptions.ConnectionError as e:
                last_error = str(e)
                if RetryStrategy.should_retry(ErrorCode.NETWORK_ERROR, attempt):
                    delay = RetryStrategy.exponential_backoff(attempt)
                    time.sleep(delay)
                    continue
                return {
                    'success': False,
                    'error': '网络连接失败，请检查网络',
                    'error_code': ErrorCode.NETWORK_ERROR.value
                }
                
            except requests.exceptions.RequestException as e:
                return {
                    'success': False,
                    'error': f'请求失败: {str(e)}',
                    'error_code': ErrorCode.OCR_ERROR.value
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': f'OCR失败: {str(e)}',
                    'error_code': ErrorCode.OCR_ERROR.value
                }
        
        # 所有重试都失败
        return {
            'success': False,
            'error': f'重试{RetryStrategy.MAX_RETRIES}次后仍然失败: {last_error}',
            'error_code': ErrorCode.SERVER_ERROR.value
        }
    
    def _get_error_message(self, error_code: ErrorCode, response: requests.Response) -> str:
        """根据错误码获取用户友好的错误消息"""
        error_messages = {
            ErrorCode.AUTH_ERROR: "API密钥无效，请检查配置",
            ErrorCode.RATE_LIMIT: "请求过于频繁，请稍后重试",
            ErrorCode.SERVER_ERROR: "服务暂时不可用，请稍后重试",
            ErrorCode.TIMEOUT: "网络连接超时，请检查网络",
        }
        return error_messages.get(error_code, f"请求失败: HTTP {response.status_code}")
    
    def _parse_default_result(self, result: Dict, model: str) -> Dict:
        """解析DeepSeek-OCR的默认响应格式"""
        if result.get("choices"):
            ocr_text = result["choices"][0]["message"]["content"]
            return {
                'success': True,
                'text': ocr_text,
                'model': model,
                'usage': result.get('usage', {}),
                'error': None
            }
        else:
            return {
                'success': False,
                'error': '未返回识别结果',
                'response': result
            }
    
    def _parse_paddleocr_result(self, result: Dict, model: str) -> Dict:
        """解析PaddleOCR-VL的响应格式"""
        if "result" in result and "layoutParsingResults" in result["result"]:
            parsing_results = result["result"]["layoutParsingResults"]
            
            markdown_texts = []
            visualize_images = []
            
            for page in parsing_results:
                if "markdown" in page and "text" in page["markdown"]:
                    markdown_texts.append(page["markdown"]["text"])
                
                if "outputImages" in page:
                    visualize_images.append(page["outputImages"])
            
            return {
                'success': True,
                'text': '\n\n'.join(markdown_texts),
                'markdown': markdown_texts,
                'visualize_images': visualize_images,
                'model': model,
                'full_result': parsing_results,
                'error': None
            }
        else:
            return {
                'success': False,
                'error': '未返回识别结果',
                'response': result
            }
    
    def _parse_pp_structure_result(self, result: Dict, model: str, 
                                   use_seal: bool, use_table: bool, 
                                   use_formula: bool) -> Dict:
        """解析PP-StructureV3的响应格式"""
        if "result" in result and "layoutParsingResults" in result["result"]:
            parsing_results = result["result"]["layoutParsingResults"]
            
            markdown_texts = []
            seal_regions = []
            table_regions = []
            formula_regions = []
            
            for page in parsing_results:
                if "markdown" in page and "text" in page["markdown"]:
                    markdown_texts.append(page["markdown"]["text"])
                
                # 提取特殊区域
                if "prunedResult" in page and "parsing_res_list" in page["prunedResult"]:
                    for block in page["prunedResult"]["parsing_res_list"]:
                        label = block.get("block_label", "")
                        if label == "seal" and use_seal:
                            seal_regions.append({
                                'content': block.get('block_content', ''),
                                'bbox': block.get('block_bbox', [])
                            })
                        elif label == "table" and use_table:
                            table_regions.append({
                                'content': block.get('block_content', ''),
                                'bbox': block.get('block_bbox', [])
                            })
                        elif label == "formula" and use_formula:
                            formula_regions.append({
                                'content': block.get('block_content', ''),
                                'bbox': block.get('block_bbox', [])
                            })
            
            return {
                'success': True,
                'text': '\n\n'.join(markdown_texts),
                'markdown': markdown_texts,
                'seals': seal_regions,
                'tables': table_regions,
                'formulas': formula_regions,
                'model': model,
                'full_result': parsing_results,
                'error': None
            }
        else:
            return {
                'success': False,
                'error': '未返回识别结果',
                'response': result
            }

    def ocr_auto(self, file_path: str, **kwargs) -> Dict:
        """
        自动选择最佳OCR模型并执行识别
        
        Args:
            file_path: 文件路径
            **kwargs: 附加参数
                - has_seal: 是否包含印章
                - has_formula: 是否包含公式
                - has_chart: 是否包含图表
                
        Returns:
            dict: OCR结果
        """
        has_seal = kwargs.get('has_seal', False)
        has_formula = kwargs.get('has_formula', False)
        has_chart = kwargs.get('has_chart', False)
        
        model = self.select_model(
            has_seal=has_seal,
            has_formula=has_formula,
            has_chart=has_chart
        )
        
        if model == "pp-structurev3":
            return self.ocr_with_pp_structure(
                file_path,
                use_seal=has_seal,
                use_formula=has_formula,
                use_chart=has_chart
            )
        elif model == "paddleocr-vl-0.9b":
            return self.ocr_with_paddleocr_vl(
                file_path,
                use_chart=has_chart
            )
        else:
            return self.ocr_with_deepseek(file_path)

