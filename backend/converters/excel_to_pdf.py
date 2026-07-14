from typing import Dict, Any
import os
import shutil
import logging
from .base import BaseConverter
from backend.utils.logger import setup_logger

class ExcelToPdfConverter(BaseConverter):
    """Excel 转 PDF 转换器 - 优化版"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['pdf']
        self.soffice_path = self._find_libreoffice()
        self.logger = setup_logger('ExcelToPdf')

    def _find_libreoffice(self) -> str:
        """查找 LibreOffice 路径"""
        # 1. 优先尝试集成路径 (resources/libreoffice)
        from conversion_core.tools.office_to_pdf import get_bundled_libreoffice_path
        bundled_path = get_bundled_libreoffice_path()
        if bundled_path and os.path.exists(bundled_path):
            return bundled_path

        # 2. 尝试系统默认路径
        paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        
        # 3. 检查环境变量 PATH
        return shutil.which("soffice")

    def _convert_with_excel(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """使用 Microsoft Excel 转换 - 优化版"""
        try:
            import comtypes.client
        except ImportError:
            raise Exception("comtypes库未安装，无法使用Excel COM转换")
        
        excel = None
        workbook = None
        
        try:
            # 转换为绝对路径
            input_path = os.path.abspath(input_path)
            output_path = os.path.abspath(output_path)
            
            self.logger.info(f"使用 Excel COM 转换: {input_path} -> {output_path}")
            
            # 启动 Excel
            excel = comtypes.client.CreateObject('Excel.Application')
            excel.Visible = False
            excel.DisplayAlerts = False
            
            # 打开工作簿
            workbook = excel.Workbooks.Open(input_path, ReadOnly=True)
            
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
            
            return {'method': 'microsoft_excel'}
            
        except Exception as e:
            self.logger.error(f"Excel COM 转换失败: {str(e)}")
            raise e
        finally:
            # 清理资源
            try:
                if workbook:
                    workbook.Close(SaveChanges=False)
            except:
                pass
            
            try:
                if excel:
                    excel.Quit()
            except:
                pass

    def _convert_with_libreoffice(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """使用 LibreOffice 转换"""
        if not self.soffice_path:
            raise Exception("LibreOffice not found")
            
        import subprocess
        
        output_dir = os.path.dirname(output_path)
        
        # 构建命令
        cmd = [
            self.soffice_path,
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            input_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            raise Exception(f"LibreOffice conversion failed: {result.stderr}")
            
        # LibreOffice 会生成同名 PDF，需要检查并重命名（如果需要）
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        generated_pdf = os.path.join(output_dir, f"{base_name}.pdf")
        
        if generated_pdf != output_path and os.path.exists(generated_pdf):
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(generated_pdf, output_path)
            
        return {'method': 'libreoffice'}

    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """执行转换（混合策略：优先Excel COM，降级LibreOffice）"""
        self.validate_input(input_path)
        self.update_progress(input_path, 5)
        
        error_messages = []
        
        # 策略1: Microsoft Excel (优化版)
        try:
            self.update_progress(input_path, 20)
            result = self._convert_with_excel(input_path, output_path)
            self.update_progress(input_path, 100)
            return {
                'success': True,
                'output_path': output_path,
                'method': result['method'],
                'size': self.get_output_size(output_path)
            }
        except Exception as e:
            error_messages.append(f"Microsoft Excel failed: {str(e)}")
            print(f"[ExcelToPdf] Excel conversion failed: {e}")
        
        # 策略2: LibreOffice
        if self.soffice_path:
            try:
                self.update_progress(input_path, 50)
                result = self._convert_with_libreoffice(input_path, output_path)
                self.update_progress(input_path, 100)
                return {
                    'success': True,
                    'output_path': output_path,
                    'method': result['method'],
                    'size': self.get_output_size(output_path)
                }
            except Exception as e:
                error_messages.append(f"LibreOffice failed: {str(e)}")
                print(f"[ExcelToPdf] LibreOffice conversion failed: {e}")
        else:
            error_messages.append("LibreOffice not available")
            print("[ExcelToPdf] LibreOffice not available")
            
        # 所有策略都失败
        return {
            'success': False,
            'error': "All conversion strategies failed.\n" + "\n".join(error_messages)
        }
