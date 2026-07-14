#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Office文件转PDF - 混合策略（COM + LibreOffice）
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


def is_frozen() -> bool:
    """检测是否在PyInstaller打包环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_app_base_path() -> str:
    """
    获取应用程序基础路径
    - 打包环境: 可执行文件所在目录
    - 开发环境: 项目根目录
    """
    if is_frozen():
        # PyInstaller打包后，sys.executable是exe文件路径
        return os.path.dirname(sys.executable)
    else:
        # 开发环境，返回backend目录
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_bundled_libreoffice_path() -> Optional[str]:
    """
    获取打包后的LibreOffice Portable路径
    打包后目录结构:
    resources/
      ├── backend/
      │   └── pdf-backend.exe
      └── libreoffice/
          └── program/soffice.exe
    """
    if is_frozen():
        # 打包环境: 从exe所在目录向上找到resources，再找libreoffice
        # base_path 是 resources/backend/dist
        base_path = get_app_base_path()
        # 向上跳两级到达 resources 目录
        resources_path = os.path.dirname(os.path.dirname(base_path))
        libreoffice_path = os.path.join(resources_path, 'libreoffice', 'program', 'soffice.exe')
        if os.path.exists(libreoffice_path):
            return libreoffice_path
    else:
        # 开发环境: get_app_base_path() 已经是项目根目录
        project_root = get_app_base_path()
        libreoffice_path = os.path.join(project_root, 'resources', 'libreoffice', 'program', 'soffice.exe')
        if os.path.exists(libreoffice_path):
            return libreoffice_path
    
    return None


class OfficeToPDF:
    """Office转PDF转换器（混合策略）"""
    
    # LibreOffice路径（相对于打包后的资源目录）
    LIBREOFFICE_PATH = None
    
    @classmethod
    def set_libreoffice_path(cls, path: str):
        """设置LibreOffice路径"""
        cls.LIBREOFFICE_PATH = path
    
    @classmethod
    def get_libreoffice_path(cls) -> Optional[str]:
        """
        获取LibreOffice路径（优先级：手动设置 > 打包路径 > 系统路径）
        """
        # 1. 优先使用手动设置的路径
        if cls.LIBREOFFICE_PATH and os.path.exists(cls.LIBREOFFICE_PATH):
            return cls.LIBREOFFICE_PATH
        
        # 2. 尝试获取打包的LibreOffice路径
        bundled_path = get_bundled_libreoffice_path()
        if bundled_path:
            return bundled_path
        
        # 3. 尝试系统安装的LibreOffice
        if sys.platform == 'win32':
            system_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
            for path in system_paths:
                if os.path.exists(path):
                    return path
        
        return None
    
    @staticmethod
    def check_office_available() -> bool:
        """
        检测Office是否可用
        
        Returns:
            bool: Office是否可用
        """
        if sys.platform != 'win32':
            return False
        
        try:
            import comtypes.client
            # 尝试创建Word应用
            word = comtypes.client.CreateObject('Word.Application')
            word.Quit()
            return True
        except Exception:
            return False
    
    @staticmethod
    def convert_with_office(input_path: str, output_path: str) -> Dict:
        """
        使用Office COM转换
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            
        Returns:
            dict: {'success': bool, 'output_file': str, 'error': str}
        """
        try:
            import comtypes.client
            
            input_path = os.path.abspath(input_path)
            output_path = os.path.abspath(output_path)
            
            ext = Path(input_path).suffix.lower()
            
            if ext in ['.doc', '.docx']:
                return OfficeToPDF._convert_word_with_com(input_path, output_path)
            elif ext in ['.xls', '.xlsx']:
                return OfficeToPDF._convert_excel_with_com(input_path, output_path)
            elif ext in ['.ppt', '.pptx']:
                return OfficeToPDF._convert_ppt_with_com(input_path, output_path)
            else:
                return {'success': False, 'error': f'不支持的文件格式: {ext}'}
                
        except Exception as e:
            return {'success': False, 'error': f'COM转换失败: {str(e)}'}
    
    @staticmethod
    def _convert_word_with_com(input_path: str, output_path: str) -> Dict:
        """Word COM转换"""
        try:
            import comtypes.client
            
            word = comtypes.client.CreateObject('Word.Application')
            word.Visible = False
            
            try:
                doc = word.Documents.Open(input_path)
                # 17 = wdFormatPDF
                doc.SaveAs(output_path, FileFormat=17)
                doc.Close()
                
                return {
                    'success': True,
                    'output_file': output_path,
                    'error': None
                }
            finally:
                word.Quit()
                
        except Exception as e:
            return {'success': False, 'error': f'Word转换失败: {str(e)}'}
    
    @staticmethod
    def _convert_excel_with_com(input_path: str, output_path: str) -> Dict:
        """Excel COM转换 - 优化版
        
        主要优化点：
        1. 智能选择纸张大小和方向（根据列数）
        2. 优化缩放策略（平衡清晰度和完整性）
        3. 自动调整列宽和行高
        4. 合理的页边距设置
        5. 高质量PDF导出
        """
        try:
            import comtypes.client
            
            excel = comtypes.client.CreateObject('Excel.Application')
            excel.Visible = False
            excel.DisplayAlerts = False
            
            try:
                workbook = excel.Workbooks.Open(input_path)
                
                # 优化每个工作表的页面设置
                for sheet in workbook.Worksheets:
                    try:
                        # 1. 精准获取实际使用区域
                        used_range = None
                        try:
                            # 强制刷新 UsedRange
                            _ = sheet.UsedRange.Rows.Count
                            
                            # 精准查找最后一行和最后一列
                            last_row_cell = sheet.Cells.Find("*", SearchOrder=1, SearchDirection=2)
                            last_col_cell = sheet.Cells.Find("*", SearchOrder=2, SearchDirection=2)
                            
                            if last_row_cell and last_col_cell:
                                last_row = last_row_cell.Row
                                last_col = last_col_cell.Column
                                used_range = sheet.Range(sheet.Cells(1, 1), sheet.Cells(last_row, last_col))
                            else:
                                used_range = sheet.UsedRange
                        except:
                            used_range = sheet.UsedRange

                        if not used_range:
                            continue

                        # 2. 先自动调整列宽和行高，确保内容完整显示
                        try:
                            used_range.Columns.AutoFit()
                            used_range.Rows.AutoFit()
                            # 增加15%的宽度余量，防止文字被截断
                            for col_idx in range(1, min(used_range.Columns.Count + 1, 100)):
                                try:
                                    col = used_range.Columns[col_idx]
                                    curr_width = col.ColumnWidth
                                    if 0 < curr_width < 100:
                                        col.ColumnWidth = curr_width * 1.15
                                except:
                                    continue
                        except Exception as e:
                            print(f"列宽调整失败: {e}")

                        # 3. 智能选择纸张大小和方向
                        setup = sheet.PageSetup
                        
                        # 计算内容宽度（列数）来决定纸张和方向
                        col_count = used_range.Columns.Count
                        
                        # 根据列数智能选择纸张和方向
                        if col_count <= 6:
                            # 少列：A4纵向
                            setup.PaperSize = 9  # xlPaperA4
                            setup.Orientation = 1  # xlPortrait
                        elif col_count <= 10:
                            # 中等列数：A4横向
                            setup.PaperSize = 9  # xlPaperA4
                            setup.Orientation = 2  # xlLandscape
                        elif col_count <= 15:
                            # 较多列：A3横向
                            setup.PaperSize = 8  # xlPaperA3
                            setup.Orientation = 2  # xlLandscape
                        else:
                            # 很多列：A3横向，允许多页宽
                            setup.PaperSize = 8  # xlPaperA3
                            setup.Orientation = 2  # xlLandscape

                        # 4. 设置缩放策略
                        if col_count <= 15:
                            # 内容不太宽，强制适应1页宽
                            setup.Zoom = False
                            setup.FitToPagesWide = 1
                            setup.FitToPagesTall = False
                        else:
                            # 内容很宽，使用固定缩放比例，保证清晰度
                            setup.Zoom = 85  # 85%缩放，平衡清晰度和完整性
                            setup.FitToPagesWide = False
                            setup.FitToPagesTall = False
                        
                        # 5. 优化页边距（单位：磅）
                        try:
                            setup.LeftMargin = excel.Application.InchesToPoints(0.2)    # 约5mm
                            setup.RightMargin = excel.Application.InchesToPoints(0.2)
                            setup.TopMargin = excel.Application.InchesToPoints(0.3)     # 约7.5mm
                            setup.BottomMargin = excel.Application.InchesToPoints(0.3)
                            setup.HeaderMargin = excel.Application.InchesToPoints(0.1)
                            setup.FooterMargin = excel.Application.InchesToPoints(0.1)
                        except:
                            # 降级方案：直接使用磅值
                            setup.LeftMargin = 14
                            setup.RightMargin = 14
                            setup.TopMargin = 22
                            setup.BottomMargin = 22
                            setup.HeaderMargin = 7
                            setup.FooterMargin = 7
                        
                        # 6. 居中显示
                        setup.CenterHorizontally = True
                        setup.CenterVertically = False

                        # 7. 设置打印区域
                        try:
                            setup.PrintArea = used_range.Address
                        except:
                            pass
                        
                        # 8. 打印质量优化
                        setup.PrintGridlines = False  # 不打印网格线
                        setup.BlackAndWhite = False   # 彩色打印
                        try:
                            setup.PrintQuality = 600  # 高质量打印
                        except:
                            pass
                                    
                    except Exception as e_sheet:
                        print(f"工作表 {sheet.Name} 优化失败: {e_sheet}")
                        continue
                
                # 导出 PDF，使用最高质量设置
                try:
                    workbook.ExportAsFixedFormat(
                        Type=0,  # xlTypePDF
                        Filename=output_path,
                        Quality=0,  # xlQualityStandard (最高质量)
                        IncludeDocProperties=True,
                        IgnorePrintAreas=False,
                        OpenAfterPublish=False
                    )
                except Exception as e_export:
                    print(f"ExportAsFixedFormat 失败: {e_export}")
                    # 降级方案
                    workbook.ExportAsFixedFormat(0, output_path)
                
                workbook.Close(False)
                
                return {
                    'success': True,
                    'output_file': output_path,
                    'error': None
                }
            finally:
                excel.Quit()
                
        except Exception as e:
            return {'success': False, 'error': f'Excel转换失败: {str(e)}'}

    @staticmethod
    def _convert_ppt_with_com(input_path: str, output_path: str) -> Dict:
        """PPT COM转换"""
        try:
            import comtypes.client
            
            ppt = comtypes.client.CreateObject('PowerPoint.Application')
            ppt.Visible = 1
            
            try:
                presentation = ppt.Presentations.Open(input_path, WithWindow=False)
                # 32 = ppSaveAsPDF
                presentation.SaveAs(output_path, 32)
                presentation.Close()
                
                return {
                    'success': True,
                    'output_file': output_path,
                    'error': None
                }
            finally:
                ppt.Quit()
                
        except Exception as e:
            return {'success': False, 'error': f'PPT转换失败: {str(e)}'}
    
    @staticmethod
    def convert_with_libreoffice(input_path: str, output_path: str,
                                 libreoffice_path: Optional[str] = None) -> Dict:
        """
        使用LibreOffice转换
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            libreoffice_path: LibreOffice可执行文件路径
            
        Returns:
            dict: {'success': bool, 'output_file': str, 'error': str}
        """
        try:
            # 确定LibreOffice路径
            if libreoffice_path is None:
                libreoffice_path = OfficeToPDF.LIBREOFFICE_PATH
            
            if libreoffice_path is None:
                # 使用统一的路径获取方法
                libreoffice_path = OfficeToPDF.get_libreoffice_path()
            
            if libreoffice_path is None or not os.path.exists(libreoffice_path):
                return {'success': False, 'error': '未找到LibreOffice'}
            
            input_path = os.path.abspath(input_path)
            output_dir = os.path.dirname(os.path.abspath(output_path))
            
            # 执行LibreOffice转换
            cmd = [
                libreoffice_path,
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                input_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'LibreOffice转换失败: {result.stderr}'
                }
            
            # 检查输出文件
            expected_output = os.path.join(
                output_dir,
                Path(input_path).stem + '.pdf'
            )
            
            if os.path.exists(expected_output):
                # 如果输出文件名不匹配，重命名
                if expected_output != output_path:
                    os.rename(expected_output, output_path)
                
                return {
                    'success': True,
                    'output_file': output_path,
                    'error': None
                }
            else:
                return {'success': False, 'error': '未生成PDF文件'}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '转换超时'}
        except Exception as e:
            return {'success': False, 'error': f'LibreOffice转换失败: {str(e)}'}
    
    @staticmethod
    def convert(input_path: str, output_path: str, 
               prefer_office: bool = True) -> Dict:
        """
        混合策略转换（优先Office，降级LibreOffice）
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            prefer_office: 是否优先使用Office
            
        Returns:
            dict: {'success': bool, 'output_file': str, 'error': str, 'method': str}
        """
        if not os.path.exists(input_path):
            return {'success': False, 'error': '文件不存在'}
        
        ext = Path(input_path).suffix.lower()
        if ext not in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
            return {'success': False, 'error': f'不支持的文件格式: {ext}'}
        
        # 策略1：优先使用Office（如果可用且偏好Office）
        if prefer_office and OfficeToPDF.check_office_available():
            result = OfficeToPDF.convert_with_office(input_path, output_path)
            if result['success']:
                result['method'] = 'Office COM'
                return result
        
        # 策略2：降级使用LibreOffice
        result = OfficeToPDF.convert_with_libreoffice(input_path, output_path)
        if result['success']:
            result['method'] = 'LibreOffice'
            return result
        
        # 策略3：如果不偏好Office但Office可用，作为最后手段
        if not prefer_office and OfficeToPDF.check_office_available():
            result = OfficeToPDF.convert_with_office(input_path, output_path)
            if result['success']:
                result['method'] = 'Office COM (fallback)'
                return result
        
        return {
            'success': False,
            'error': '所有转换方法都失败',
            'method': None
        }

