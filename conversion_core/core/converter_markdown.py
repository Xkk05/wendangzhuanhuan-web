import os
import logging
import fitz
from conversion_core.core.base import Converter


logger = logging.getLogger(__name__)


class MarkdownConverter(Converter):
    """PDF转Markdown转换器"""
    
    def convert(self, file_path):
        """
        将PDF转换为Markdown
        """
        self.update_progress(file_path, 10)
        output_file = self.get_output_filename(file_path, 'md')
        logger.info("开始PDF转Markdown: %s -> %s", file_path, output_file)
        doc = None
        failed_pages = []
        try:
            try:
                doc = fitz.open(file_path)
            except Exception as e:
                logger.exception("打开PDF失败: %s", file_path)
                message = str(e)
                lower = message.lower()
                if "encrypt" in lower or "password" in lower:
                    return {'success': False, 'error': 'PDF文件已加密，无法直接转换'}
                if "format error" in lower or "xref" in lower or "repair" in lower:
                    return {'success': False, 'error': 'PDF文件可能已损坏，无法转换'}
                return {'success': False, 'error': f'PDF转Markdown失败: {message}'}
            if doc.page_count == 0:
                logger.info("PDF文件为空: %s", file_path)
                return {'success': False, 'error': 'PDF文件为空'}
            total_pages = doc.page_count
            md_content = []
            logger.info("PDF页数: %d", total_pages)
            self.update_progress(file_path, 20)
            for page_idx in range(total_pages):
                progress = 20 + int(((page_idx + 1) / total_pages) * 70)
                self.update_progress(file_path, progress)
                page = doc[page_idx]
                try:
                    text = page.get_text("markdown")
                except ValueError:
                    logger.warning("第%d页markdown提取失败，使用text模式降级", page_idx)
                    text = page.get_text("text")
                except Exception as e:
                    logger.exception("第%d页文本提取异常", page_idx)
                    failed_pages.append(page_idx)
                    continue
                if text.strip():
                    md_content.append(text)
                    md_content.append("\n\n---\n\n")
            if not md_content and failed_pages:
                logger.error("所有页面解析失败: %s", file_path)
                return {'success': False, 'error': 'PDF转Markdown失败: 所有页面解析失败', 'failed_pages': failed_pages}
            with open(output_file, 'w', encoding='utf-8') as f:
                content = "".join(md_content)
                logger.info("写入Markdown文件: %s, 长度: %d", output_file, len(content))
                f.write(content)
            self.update_progress(file_path, 100)
            result = {'success': True, 'output_file': output_file}
            if failed_pages:
                result['partial_failed'] = True
                result['failed_pages'] = failed_pages
                logger.warning("部分页面解析失败: %s", failed_pages)
            logger.info("PDF转Markdown完成: %s", file_path)
            return result
        except Exception as e:
            logger.exception("PDF转Markdown失败: %s", file_path)
            return {'success': False, 'error': f'PDF转Markdown失败: {str(e)}'}
        finally:
            if doc is not None:
                doc.close()
