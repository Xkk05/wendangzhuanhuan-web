import os
from .base import BaseConverter
from .pdf_to_docx import PdfToDocxConverter
from typing import Dict, Any


class PdfToRtfConverter(BaseConverter):
    """PDF 到 RTF 转换器 - 通过DOCX中间格式"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['rtf']
        self.pdf_to_docx = PdfToDocxConverter()
    
    def convert(self, input_path: str, output_path: str, **options) -> Dict[str, Any]:
        """将 PDF 转换为 RTF（通过DOCX中间格式）"""
        temp_docx_path = None
        try:
            self.validate_input(input_path)
            self.update_progress(input_path, 10)
            
            # 生成临时DOCX文件
            base_dir = os.path.dirname(output_path) or os.getcwd()
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            temp_docx_path = os.path.join(base_dir, base_name + "_temp.docx")
            
            # 第一步：PDF -> DOCX
            self.pdf_to_docx.convert(input_path, temp_docx_path, **options)
            self.update_progress(input_path, 50)
            
            # 第二步：DOCX -> RTF (使用pypandoc)
            try:
                import pypandoc
                pypandoc.convert_file(temp_docx_path, 'rtf', outputfile=output_path)
                self.update_progress(input_path, 100)
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'size': self.get_output_size(output_path),
                    'method': 'pdf->docx->rtf (pypandoc)'
                }
            except ImportError:
                # 降级方案：使用python-docx读取，手动生成RTF
                from docx import Document
                doc = Document(temp_docx_path)
                
                rtf_content = self._generate_rtf(doc)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(rtf_content)
                
                self.update_progress(input_path, 100)
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'size': self.get_output_size(output_path),
                    'method': 'pdf->docx->rtf (manual)'
                }
            
        except Exception as e:
            self.cleanup_on_error(output_path)
            raise Exception(f"PDF to RTF conversion failed: {str(e)}")
        finally:
            # 清理临时DOCX文件
            if temp_docx_path and os.path.exists(temp_docx_path):
                try:
                    os.remove(temp_docx_path)
                except:
                    pass
    
    def _generate_rtf(self, doc) -> str:
        """手动生成支持中文的RTF格式"""
        # RTF头部，指定字体表和字符集
        rtf_header = r"""{\rtf1\ansi\ansicpg936\deff0\nouicompat\deflang2052
{\fonttbl{\f0\fnil\fcharset134 Microsoft YaHei;}{\f1\fnil\fcharset0 Calibri;}}
{\colortbl ;\red0\green0\blue0;}
\viewkind4\uc1"""
        
        rtf_footer = r"}"
        
        content = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                # 转义特殊字符
                text = text.replace('\\', '\\\\')
                text = text.replace('{', '\\{')
                text = text.replace('}', '\\}')
                
                # 将中文字符转换为Unicode转义
                rtf_text = ""
                for char in text:
                    if ord(char) > 127:  # 非ASCII字符
                        # RTF使用\uN?格式，N是Unicode码点
                        rtf_text += f"\\u{ord(char)}?"
                    else:
                        rtf_text += char
                
                # 添加段落，使用中文字体
                content.append(f"\\pard\\f0\\fs22 {rtf_text}\\par")
        
        rtf_body = "\n".join(content)
        
        return f"{rtf_header}\n{rtf_body}\n{rtf_footer}"
