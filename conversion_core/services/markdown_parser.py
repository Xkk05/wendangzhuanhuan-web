#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Markdown解析器 - 解析OCR返回的Markdown格式文本
支持: Markdown表格、HTML表格、LaTeX公式
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class TableData:
    """表格数据模型"""
    rows: List[List[str]] = field(default_factory=list)
    headers: List[str] = field(default_factory=list)
    row_count: int = 0
    col_count: int = 0
    source: str = "markdown"


@dataclass
class FormulaData:
    """公式数据模型"""
    latex: str
    display: bool  # True=块级公式, False=行内公式
    position: int


@dataclass
class HeadingData:
    """标题数据模型"""
    level: int
    text: str
    position: int


@dataclass 
class ContentBlock:
    """内容块模型 - 用于保持内容顺序"""
    type: str  # text, formula, table, heading, image
    content: any
    position: int


class HTMLTableParser(HTMLParser):
    """HTML表格解析器"""
    
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = None
        self.current_row = None
        self.current_cell = ""
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.in_header = False
        self.header_row = []
    
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'table':
            self.in_table = True
            self.current_table = []
            self.header_row = []
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ('td', 'th') and self.in_row:
            self.in_cell = True
            self.in_header = (tag == 'th')
            self.current_cell = ""
    
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'table' and self.in_table:
            if self.current_table or self.header_row:
                self.tables.append({
                    'headers': self.header_row,
                    'rows': self.current_table if self.current_table else []
                })
            self.in_table = False
            self.current_table = None
            self.header_row = []
        elif tag == 'tr' and self.in_row:
            if self.current_row is not None:
                if self.in_header and not self.header_row:
                    self.header_row = self.current_row
                else:
                    if self.current_table is not None:
                        self.current_table.append(self.current_row)
            self.in_row = False
            self.current_row = None
            self.in_header = False
        elif tag in ('td', 'th') and self.in_cell:
            if self.current_row is not None:
                self.current_row.append(self.current_cell.strip())
            self.in_cell = False
            self.current_cell = ""
    
    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data
    
    def get_tables(self) -> List[Dict]:
        return self.tables


class MarkdownParser:
    """解析OCR返回的Markdown结果"""
    
    # HTML相关模式
    HTML_TABLE_PATTERN = re.compile(r'<table[^>]*>.*?</table>', re.DOTALL | re.IGNORECASE)
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>', re.DOTALL)
    HTML_BLOCK_PATTERN = re.compile(r'<(?:div|html|body|center)[^>]*>|</(?:div|html|body|center)>', re.IGNORECASE)
    
    # LaTeX公式模式 - 支持更多格式
    BLOCK_FORMULA_PATTERN = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
    INLINE_FORMULA_PATTERN = re.compile(r'(?<!\$)\$(?!\$)([^\$]+?)\$(?!\$)')
    # 支持方括号格式的公式 [\hat{c}{=}\frac{1}{\mathtt{e}}]
    BRACKET_FORMULA_PATTERN = re.compile(r'\[([^[\]]*(?:\\[^[\]]*)*[^[\]]*)\]')
    # 支持花括号格式的公式 {\hat{c}{=}\frac{1}{\mathtt{e}}}
    BRACE_FORMULA_PATTERN = re.compile(r'\{([^{}]*(?:\\[^{}]*)*[^{}]*)\}')
    
    # Markdown模式
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    MD_TABLE_ROW_PATTERN = re.compile(r'^\|.+\|$', re.MULTILINE)
    
    def parse(self, markdown_text: str) -> Dict:
        """解析Markdown文本，返回结构化内容"""
        if not markdown_text:
            return {
                "paragraphs": [],
                "tables": [],
                "images": [],
                "headings": [],
                "formulas": [],
                "content_blocks": []
            }
        
        # 提取各类元素
        tables = self.extract_tables(markdown_text)
        headings = self.extract_headings(markdown_text)
        images = self.extract_images(markdown_text)
        formulas = self.extract_formulas(markdown_text)
        
        # 清理文本后提取段落
        clean_text = self._clean_text_for_paragraphs(markdown_text)
        paragraphs = self._extract_clean_paragraphs(clean_text)
        
        return {
            "paragraphs": paragraphs,
            "tables": tables,
            "images": images,
            "headings": headings,
            "formulas": formulas
        }
    
    def _clean_text_for_paragraphs(self, text: str) -> str:
        """清理文本，移除HTML、表格等，保留公式占位符"""
        # 移除HTML表格
        text = self.HTML_TABLE_PATTERN.sub('[TABLE]', text)
        # 移除其他HTML标签
        text = self.HTML_BLOCK_PATTERN.sub('', text)
        text = self.HTML_TAG_PATTERN.sub('', text)
        
        # 将块级公式替换为占位符
        text = self.BLOCK_FORMULA_PATTERN.sub('[BLOCK_FORMULA]', text)
        
        # 将行内公式替换为占位符
        text = self.INLINE_FORMULA_PATTERN.sub('[FORMULA]', text)
        
        return text
    
    def _extract_clean_paragraphs(self, text: str) -> List[str]:
        """从清理后的文本中提取段落"""
        paragraphs = []
        lines = text.split('\n')
        
        current_para = []
        in_table = False
        in_code = False
        
        for line in lines:
            stripped = line.strip()
            
            # 代码块
            if stripped.startswith('```'):
                in_code = not in_code
                continue
            if in_code:
                continue
            
            # Markdown表格
            if stripped.startswith('|') and stripped.endswith('|'):
                in_table = True
                if current_para:
                    para = ' '.join(current_para).strip()
                    if para and para not in ['[TABLE]', '[BLOCK_FORMULA]', '[FORMULA]']:
                        paragraphs.append(para)
                    current_para = []
                continue
            elif in_table and not stripped:
                in_table = False
                continue
            elif in_table:
                continue
            
            # 标题
            if stripped.startswith('#'):
                if current_para:
                    para = ' '.join(current_para).strip()
                    if para and para not in ['[TABLE]', '[BLOCK_FORMULA]', '[FORMULA]']:
                        paragraphs.append(para)
                    current_para = []
                continue
            
            # 跳过占位符行
            if stripped in ['[TABLE]', '[BLOCK_FORMULA]']:
                if current_para:
                    para = ' '.join(current_para).strip()
                    if para and para not in ['[TABLE]', '[BLOCK_FORMULA]', '[FORMULA]']:
                        paragraphs.append(para)
                    current_para = []
                continue
            
            # 图片
            if self.IMAGE_PATTERN.match(stripped):
                continue
            
            # 水平线
            if stripped in ['---', '***', '___']:
                if current_para:
                    para = ' '.join(current_para).strip()
                    if para:
                        paragraphs.append(para)
                    current_para = []
                continue
            
            # 空行
            if not stripped:
                if current_para:
                    para = ' '.join(current_para).strip()
                    if para and para not in ['[TABLE]', '[BLOCK_FORMULA]', '[FORMULA]']:
                        paragraphs.append(para)
                    current_para = []
            else:
                # 清理行内占位符
                cleaned = stripped.replace('[FORMULA]', '').strip()
                if cleaned:
                    current_para.append(cleaned)
        
        # 最后一个段落
        if current_para:
            para = ' '.join(current_para).strip()
            if para and para not in ['[TABLE]', '[BLOCK_FORMULA]', '[FORMULA]']:
                paragraphs.append(para)
        
        return paragraphs

    def extract_tables(self, markdown_text: str) -> List[TableData]:
        """提取所有表格（HTML和Markdown格式）"""
        tables = []
        
        if not markdown_text:
            return tables
        
        # 1. 提取HTML表格
        html_tables = self._extract_html_tables(markdown_text)
        tables.extend(html_tables)
        
        # 2. 移除HTML后提取Markdown表格
        text_no_html = self.HTML_TABLE_PATTERN.sub('', markdown_text)
        text_no_html = self.HTML_BLOCK_PATTERN.sub('', text_no_html)
        md_tables = self._extract_markdown_tables(text_no_html)
        tables.extend(md_tables)
        
        return tables
    
    def _extract_html_tables(self, text: str) -> List[TableData]:
        """提取HTML表格"""
        tables = []
        
        for match in self.HTML_TABLE_PATTERN.finditer(text):
            html_table = match.group(0)
            try:
                parser = HTMLTableParser()
                parser.feed(html_table)
                
                for table_dict in parser.get_tables():
                    headers = table_dict.get('headers', [])
                    rows = table_dict.get('rows', [])
                    
                    # 如果没有表头但有数据，第一行作为表头
                    if not headers and rows:
                        headers = rows[0]
                        rows = rows[1:] if len(rows) > 1 else []
                    
                    all_rows = ([headers] if headers else []) + rows
                    col_count = max(len(r) for r in all_rows) if all_rows else 0
                    
                    if rows or headers:
                        tables.append(TableData(
                            rows=rows,
                            headers=headers,
                            row_count=len(rows),
                            col_count=col_count,
                            source="html"
                        ))
            except Exception:
                continue
        
        return tables
    
    def _extract_markdown_tables(self, text: str) -> List[TableData]:
        """提取Markdown表格"""
        tables = []
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('|') and line.endswith('|'):
                table_lines = [line]
                i += 1
                
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith('|') and next_line.endswith('|'):
                        table_lines.append(next_line)
                        i += 1
                    elif not next_line:
                        i += 1
                        break
                    else:
                        break
                
                table = self._parse_md_table(table_lines)
                if table and (table.row_count > 0 or table.headers):
                    tables.append(table)
            else:
                i += 1
        
        return tables
    
    def _parse_md_table(self, lines: List[str]) -> Optional[TableData]:
        """解析Markdown表格行"""
        if not lines:
            return None
        
        rows = []
        headers = []
        separator_found = False
        
        for idx, line in enumerate(lines):
            line = line.strip()
            if line.startswith('|'):
                line = line[1:]
            if line.endswith('|'):
                line = line[:-1]
            
            cells = [c.strip() for c in line.split('|')]
            
            # 检查分隔行
            if all(self._is_separator(c) for c in cells):
                separator_found = True
                continue
            
            if not separator_found and idx == 0:
                headers = cells
            else:
                rows.append(cells)
        
        if not separator_found and headers:
            rows.insert(0, headers)
            headers = []
        
        all_rows = ([headers] if headers else []) + rows
        col_count = max(len(r) for r in all_rows) if all_rows else 0
        
        return TableData(
            rows=rows,
            headers=headers,
            row_count=len(rows),
            col_count=col_count,
            source="markdown"
        )
    
    def _is_separator(self, cell: str) -> bool:
        """检查是否为表格分隔符"""
        cell = cell.strip()
        if not cell:
            return True
        return all(c in '-: ' for c in cell) and '-' in cell

    def extract_formulas(self, markdown_text: str) -> List[FormulaData]:
        """提取LaTeX公式 - 支持多种格式"""
        formulas = []
        
        if not markdown_text:
            return formulas
        
        # 块级公式 $$...$$
        for match in self.BLOCK_FORMULA_PATTERN.finditer(markdown_text):
            latex = match.group(1)
            if latex:
                formulas.append(FormulaData(
                    latex=latex.strip(),
                    display=True,
                    position=match.start()
                ))
        
        # 获取已处理的位置范围
        processed_ranges = [(m.start(), m.end()) for m in self.BLOCK_FORMULA_PATTERN.finditer(markdown_text)]
        
        # 行内公式 $...$（排除块级公式位置）
        for match in self.INLINE_FORMULA_PATTERN.finditer(markdown_text):
            pos = match.start()
            # 检查是否在已处理范围内
            in_processed = any(start <= pos < end for start, end in processed_ranges)
            if not in_processed:
                latex = match.group(1)
                if latex and self._is_likely_formula(latex):
                    formulas.append(FormulaData(
                        latex=latex.strip(),
                        display=False,
                        position=pos
                    ))
                    processed_ranges.append((match.start(), match.end()))
        
        # 方括号格式公式 [\hat{c}{=}\frac{1}{\mathtt{e}}]
        for match in self.BRACKET_FORMULA_PATTERN.finditer(markdown_text):
            pos = match.start()
            # 检查是否在已处理范围内
            in_processed = any(start <= pos < end for start, end in processed_ranges)
            if not in_processed:
                latex = match.group(1)
                if latex and self._is_likely_formula(latex):
                    formulas.append(FormulaData(
                        latex=latex.strip(),
                        display=False,
                        position=pos
                    ))
                    processed_ranges.append((match.start(), match.end()))
        
        # 花括号格式公式 {\hat{c}{=}\frac{1}{\mathtt{e}}}
        for match in self.BRACE_FORMULA_PATTERN.finditer(markdown_text):
            pos = match.start()
            # 检查是否在已处理范围内
            in_processed = any(start <= pos < end for start, end in processed_ranges)
            if not in_processed:
                latex = match.group(1)
                if latex and self._is_likely_formula(latex):
                    formulas.append(FormulaData(
                        latex=latex.strip(),
                        display=False,
                        position=pos
                    ))
        
        formulas.sort(key=lambda f: f.position)
        return formulas
    
    def _is_likely_formula(self, text: str) -> bool:
        """判断文本是否可能是LaTeX公式"""
        if not text or len(text) < 2:
            return False
        
        # LaTeX命令特征
        latex_indicators = [
            '\\frac', '\\hat', '\\mathtt', '\\sqrt', '\\sum', '\\int', 
            '\\alpha', '\\beta', '\\gamma', '\\delta', '\\epsilon',
            '\\theta', '\\lambda', '\\mu', '\\pi', '\\sigma', '\\phi',
            '\\psi', '\\omega', '\\Gamma', '\\Delta', '\\Theta', '\\Lambda',
            '\\Pi', '\\Sigma', '\\Phi', '\\Psi', '\\Omega',
            '\\left', '\\right', '\\begin', '\\end', '\\cdot', '\\times',
            '\\div', '\\pm', '\\mp', '\\leq', '\\geq', '\\neq', '\\approx',
            '\\infty', '\\partial', '\\nabla', '\\in', '\\subset', '\\cup',
            '\\cap', '\\emptyset', '\\forall', '\\exists', '\\lim', '\\log',
            '\\ln', '\\sin', '\\cos', '\\tan', '\\sec', '\\csc', '\\cot'
        ]
        
        # 检查是否包含LaTeX命令
        for indicator in latex_indicators:
            if indicator in text:
                return True
        
        # 检查是否包含数学符号组合
        math_patterns = [
            r'\\[a-zA-Z]+',  # LaTeX命令
            r'\^[{]?[^}]*[}]?',  # 上标
            r'_[{]?[^}]*[}]?',   # 下标
            r'[{}].*[{}]',       # 花括号组合
        ]
        
        for pattern in math_patterns:
            if re.search(pattern, text):
                return True
        
        return False

    def extract_headings(self, markdown_text: str) -> List[HeadingData]:
        """提取标题"""
        headings = []
        
        if not markdown_text:
            return headings
        
        for match in self.HEADING_PATTERN.finditer(markdown_text):
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append(HeadingData(level=level, text=text, position=match.start()))
        
        return headings
    
    def extract_images(self, markdown_text: str) -> List[Dict]:
        """提取图片"""
        images = []
        
        if not markdown_text:
            return images
        
        for match in self.IMAGE_PATTERN.finditer(markdown_text):
            images.append({
                "alt": match.group(1),
                "url": match.group(2),
                "position": match.start()
            })
        
        return images
