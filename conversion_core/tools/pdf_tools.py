#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF工具箱 - 合并/压缩/拆分/解密/提取
"""

import os
from typing import List, Dict
import pypdf
import pikepdf


class PDFTools:
    """PDF工具类"""
    
    @staticmethod
    def merge_pdfs(file_list: List[str], output_path: str) -> Dict:
        """
        合并多个PDF文件
        
        Args:
            file_list: PDF文件路径列表
            output_path: 输出文件路径
            
        Returns:
            dict: {'success': bool, 'output_file': str, 'error': str}
        """
        try:
            if not file_list:
                return {'success': False, 'error': '没有提供文件'}
            
            merger = pypdf.PdfMerger()
            
            for pdf_file in file_list:
                if not os.path.exists(pdf_file):
                    return {'success': False, 'error': f'文件不存在: {pdf_file}'}
                
                merger.append(pdf_file)
            
            merger.write(output_path)
            merger.close()
            
            return {
                'success': True,
                'output_file': output_path,
                'error': None
            }
            
        except Exception as e:
            return {'success': False, 'error': f'合并失败: {str(e)}'}
    
    @staticmethod
    def compress_pdf(input_path: str, output_path: str, 
                    image_quality: int = 75) -> Dict:
        """
        压缩PDF文件 - 智能选择最佳压缩策略
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            image_quality: 图片质量 (1-100)，默认75
            
        Returns:
            dict: {'success': bool, 'output_file': str, 'error': str, 'compression_ratio': float}
        """
        import shutil
        
        temp_files = []
        
        def cleanup_temp_files():
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass
        
        try:
            if not os.path.exists(input_path):
                return {'success': False, 'error': '文件不存在'}
            
            original_size = os.path.getsize(input_path)
            best_size = original_size
            best_output = None
            
            # 策略1: pikepdf流压缩 + 清理冗余对象
            temp_output1 = output_path + '.temp1'
            temp_files.append(temp_output1)
            try:
                with pikepdf.open(input_path) as pdf:
                    # 移除未使用的对象和优化结构
                    pdf.remove_unreferenced_resources()
                    pdf.save(
                        temp_output1,
                        compress_streams=True,
                        stream_decode_level=pikepdf.StreamDecodeLevel.generalized,
                        object_stream_mode=pikepdf.ObjectStreamMode.generate,
                        recompress_flate=True,
                        normalize_content=True,
                        linearize=False  # 不线性化，减少文件大小
                    )
                
                size1 = os.path.getsize(temp_output1)
                if size1 < best_size:
                    best_size = size1
                    best_output = temp_output1
            except Exception as e:
                print(f"策略1失败: {e}")
            
            # 策略2: 使用PyMuPDF压缩内嵌图片（不转换整页为图片）
            temp_output2 = output_path + '.temp2'
            temp_files.append(temp_output2)
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(input_path)
                
                # 检测PDF是否包含大量图片
                has_images = False
                total_image_size = 0
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    image_list = page.get_images(full=True)
                    if image_list:
                        has_images = True
                        for img in image_list:
                            xref = img[0]
                            try:
                                base_image = doc.extract_image(xref)
                                if base_image:
                                    total_image_size += len(base_image.get("image", b""))
                            except:
                                pass
                
                # 只有当图片占比较大时才进行图片压缩
                image_ratio = total_image_size / original_size if original_size > 0 else 0
                
                if has_images and image_ratio > 0.3:  # 图片占30%以上才压缩图片
                    # 压缩内嵌图片而不是转换整页
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        image_list = page.get_images(full=True)
                        
                        for img in image_list:
                            xref = img[0]
                            try:
                                base_image = doc.extract_image(xref)
                                if not base_image:
                                    continue
                                
                                image_bytes = base_image["image"]
                                image_ext = base_image["ext"]
                                
                                # 只压缩较大的图片
                                if len(image_bytes) < 50000:  # 小于50KB跳过
                                    continue
                                
                                # 使用PIL压缩图片
                                from PIL import Image
                                import io
                                
                                img_pil = Image.open(io.BytesIO(image_bytes))
                                
                                # 转换为RGB（如果需要）
                                if img_pil.mode in ('RGBA', 'P'):
                                    img_pil = img_pil.convert('RGB')
                                
                                # 如果图片很大，缩小尺寸
                                max_dim = 1500
                                if img_pil.width > max_dim or img_pil.height > max_dim:
                                    ratio = min(max_dim / img_pil.width, max_dim / img_pil.height)
                                    new_size = (int(img_pil.width * ratio), int(img_pil.height * ratio))
                                    img_pil = img_pil.resize(new_size, Image.LANCZOS)
                                
                                # 压缩为JPEG
                                output_buffer = io.BytesIO()
                                img_pil.save(output_buffer, format='JPEG', quality=image_quality, optimize=True)
                                compressed_bytes = output_buffer.getvalue()
                                
                                # 只有压缩后更小才替换
                                if len(compressed_bytes) < len(image_bytes) * 0.9:
                                    # 替换图片
                                    page.replace_image(xref, stream=compressed_bytes)
                                    
                            except Exception as img_err:
                                # 单个图片处理失败不影响整体
                                continue
                    
                    # 保存压缩后的PDF
                    doc.save(temp_output2, garbage=4, deflate=True, clean=True)
                    doc.close()
                    
                    size2 = os.path.getsize(temp_output2)
                    if size2 < best_size:
                        best_size = size2
                        best_output = temp_output2
                else:
                    doc.close()
                    
            except ImportError:
                print("PyMuPDF或PIL未安装，跳过图片压缩策略")
            except Exception as e:
                print(f"策略2失败: {e}")
            
            # 策略3: PyMuPDF的garbage collection和deflate
            temp_output3 = output_path + '.temp3'
            temp_files.append(temp_output3)
            try:
                import fitz
                doc = fitz.open(input_path)
                doc.save(
                    temp_output3,
                    garbage=4,      # 最大程度清理
                    deflate=True,   # 压缩流
                    clean=True,     # 清理内容流
                    pretty=False,   # 不美化（减少空白）
                    linear=False    # 不线性化
                )
                doc.close()
                
                size3 = os.path.getsize(temp_output3)
                if size3 < best_size:
                    best_size = size3
                    best_output = temp_output3
            except ImportError:
                pass
            except Exception as e:
                print(f"策略3失败: {e}")
            
            # 选择最佳结果
            if best_output and best_size < original_size:
                shutil.move(best_output, output_path)
                temp_files.remove(best_output)
                cleanup_temp_files()
                
                compression_ratio = (1 - best_size / original_size) * 100
                
                return {
                    'success': True,
                    'output_file': output_path,
                    'error': None,
                    'compression_ratio': round(compression_ratio, 2),
                    'original_size': original_size,
                    'compressed_size': best_size
                }
            else:
                # 压缩后更大或相同，复制原文件
                cleanup_temp_files()
                shutil.copy2(input_path, output_path)
                
                return {
                    'success': True,
                    'output_file': output_path,
                    'error': None,
                    'compression_ratio': 0.0,
                    'original_size': original_size,
                    'compressed_size': original_size,
                    'message': '文件已优化或无法进一步压缩'
                }
            
        except Exception as e:
            cleanup_temp_files()
            return {'success': False, 'error': f'压缩失败: {str(e)}'}
    
    @staticmethod
    def split_pdf(input_path: str, output_dir: str, 
                  split_mode: str = 'pages', **kwargs) -> Dict:
        """
        拆分PDF文件
        
        Args:
            input_path: 输入文件路径
            output_dir: 输出目录
            split_mode: 拆分模式
                - 'pages': 按固定页数拆分 (需要 pages_per_file)
                - 'range': 按页码范围拆分 (需要 ranges: [[1,5], [6,10]])
                - 'single': 每页一个文件
            **kwargs: 附加参数
                - pages_per_file: 每个文件的页数 (split_mode='pages')
                - ranges: 页码范围列表 (split_mode='range')
                
        Returns:
            dict: {'success': bool, 'output_files': list, 'error': str}
        """
        try:
            if not os.path.exists(input_path):
                return {'success': False, 'error': '文件不存在'}
            
            os.makedirs(output_dir, exist_ok=True)
            
            reader = pypdf.PdfReader(input_path)
            total_pages = len(reader.pages)
            
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_files = []
            
            if split_mode == 'single':
                # 每页一个文件
                for page_num in range(total_pages):
                    writer = pypdf.PdfWriter()
                    writer.add_page(reader.pages[page_num])
                    
                    output_file = os.path.join(output_dir, f"{base_name}_page_{page_num + 1}.pdf")
                    with open(output_file, 'wb') as f:
                        writer.write(f)
                    output_files.append(output_file)
                    
            elif split_mode == 'pages':
                # 按固定页数拆分
                pages_per_file = kwargs.get('pages_per_file', 10)
                file_index = 1
                
                for start_page in range(0, total_pages, pages_per_file):
                    writer = pypdf.PdfWriter()
                    end_page = min(start_page + pages_per_file, total_pages)
                    
                    for page_num in range(start_page, end_page):
                        writer.add_page(reader.pages[page_num])
                    
                    output_file = os.path.join(output_dir, f"{base_name}_part_{file_index}.pdf")
                    with open(output_file, 'wb') as f:
                        writer.write(f)
                    output_files.append(output_file)
                    file_index += 1
                    
            elif split_mode == 'range':
                # 按页码范围拆分
                ranges = kwargs.get('ranges', [])
                if not ranges:
                    return {'success': False, 'error': '未提供页码范围'}

                for range_item in ranges:
                    if not isinstance(range_item, (list, tuple)) or len(range_item) != 2:
                        return {'success': False, 'error': f'无效的页码范围: {range_item}'}
                    start, end = range_item
                    if not isinstance(start, int) or not isinstance(end, int):
                        return {'success': False, 'error': f'无效的页码范围: {start}-{end}'}
                    if start < 1 or end < 1:
                        return {'success': False, 'error': '页码必须大于等于 1'}
                    if end < start:
                        return {'success': False, 'error': f'无效的页码范围: 起始页 {start} 大于结束页 {end}'}
                    if start > total_pages or end > total_pages:
                        return {
                            'success': False,
                            'error': f'页码范围超出文档页数: 文档共 {total_pages} 页，范围 {start}-{end}'
                        }

                for idx, (start, end) in enumerate(ranges, 1):
                    writer = pypdf.PdfWriter()
                    
                    for page_num in range(start - 1, min(end, total_pages)):
                        writer.add_page(reader.pages[page_num])
                    
                    output_file = os.path.join(output_dir, f"{base_name}_range_{idx}.pdf")
                    with open(output_file, 'wb') as f:
                        writer.write(f)
                    output_files.append(output_file)
            
            else:
                return {'success': False, 'error': f'不支持的拆分模式: {split_mode}'}
            
            return {
                'success': True,
                'output_files': output_files,
                'error': None
            }
            
        except Exception as e:
            return {'success': False, 'error': f'拆分失败: {str(e)}'}
    
    @staticmethod
    def extract_pages(input_path: str, output_path: str, 
                     page_list: List[int]) -> Dict:
        """
        提取指定页面
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            page_list: 页码列表 (从1开始)
            
        Returns:
            dict: {'success': bool, 'output_file': str, 'error': str}
        """
        try:
            if not os.path.exists(input_path):
                return {'success': False, 'error': '文件不存在'}
            
            if not page_list:
                return {'success': False, 'error': '没有指定页码'}
            
            reader = pypdf.PdfReader(input_path)
            total_pages = len(reader.pages)
            writer = pypdf.PdfWriter()
            
            for page_num in page_list:
                if 1 <= page_num <= total_pages:
                    writer.add_page(reader.pages[page_num - 1])
                else:
                    return {'success': False, 'error': f'页码超出范围: {page_num}'}
            
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            return {
                'success': True,
                'output_file': output_path,
                'error': None
            }
            
        except Exception as e:
            return {'success': False, 'error': f'提取失败: {str(e)}'}
    
    @staticmethod
    def unlock_pdf(input_path: str, output_path: str, password: str) -> Dict:
        """
        解除PDF密码保护
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            password: 密码
            
        Returns:
            dict: {'success': bool, 'output_file': str, 'error': str, 'message': str}
        """
        try:
            if not os.path.exists(input_path):
                return {'success': False, 'error': '文件不存在'}
            
            # 首先检查文件是否加密
            try:
                reader = pypdf.PdfReader(input_path)
                
                if not reader.is_encrypted:
                    # 文件没有密码保护，直接复制
                    import shutil
                    shutil.copy2(input_path, output_path)
                    return {
                        'success': True,
                        'output_file': output_path,
                        'error': None,
                        'message': '该PDF文件没有密码保护'
                    }
                
                # 文件有密码保护，尝试解密
                if not password:
                    return {'success': False, 'error': '该PDF文件有密码保护，请输入密码'}
                
                # 尝试解密
                decrypt_result = reader.decrypt(password)
                if decrypt_result == 0:
                    return {'success': False, 'error': '密码错误，请检查密码是否正确'}
                elif decrypt_result == 1:
                    # 用户密码正确
                    pass
                elif decrypt_result == 2:
                    # 所有者密码正确
                    pass
                else:
                    return {'success': False, 'error': '密码验证失败'}
                
                # 解密成功，保存文件
                writer = pypdf.PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                
                with open(output_path, 'wb') as f:
                    writer.write(f)
                
                return {
                    'success': True,
                    'output_file': output_path,
                    'error': None,
                    'message': '密码验证成功，PDF已解密'
                }
                
            except Exception as pypdf_error:
                # pypdf失败，尝试pikepdf
                try:
                    # 先检查是否需要密码
                    try:
                        with pikepdf.open(input_path) as test_pdf:
                            # 如果能直接打开，说明没有密码
                            test_pdf.save(output_path)
                            return {
                                'success': True,
                                'output_file': output_path,
                                'error': None,
                                'message': '该PDF文件没有密码保护'
                            }
                    except pikepdf.PasswordError:
                        # 需要密码
                        if not password:
                            return {'success': False, 'error': '该PDF文件有密码保护，请输入密码'}
                        
                        # 尝试用密码打开
                        with pikepdf.open(input_path, password=password) as pdf:
                            pdf.save(output_path)
                        
                        return {
                            'success': True,
                            'output_file': output_path,
                            'error': None,
                            'message': '密码验证成功，PDF已解密'
                        }
                        
                except pikepdf.PasswordError:
                    return {'success': False, 'error': '密码错误，请检查密码是否正确'}
                except Exception as pikepdf_error:
                    return {'success': False, 'error': f'解密失败: {str(pikepdf_error)}'}
                    
        except Exception as e:
            return {'success': False, 'error': f'处理PDF文件时出错: {str(e)}'}
    
    @staticmethod
    def get_pdf_info(input_path: str) -> Dict:
        """
        获取PDF信息
        
        Args:
            input_path: 输入文件路径
            
        Returns:
            dict: {'success': bool, 'info': dict, 'error': str}
        """
        try:
            if not os.path.exists(input_path):
                return {'success': False, 'error': '文件不存在'}
            
            reader = pypdf.PdfReader(input_path)
            
            info = {
                'pages': len(reader.pages),
                'encrypted': reader.is_encrypted,
                'metadata': {}
            }
            
            # 获取元数据
            if reader.metadata:
                for key, value in reader.metadata.items():
                    info['metadata'][key] = str(value)
            
            return {
                'success': True,
                'info': info,
                'error': None
            }
            
        except Exception as e:
            return {'success': False, 'error': f'获取信息失败: {str(e)}'}

