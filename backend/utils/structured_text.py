from __future__ import annotations

import html
import unicodedata
from typing import Any, Iterable, List


XML_BLOCK_TAGS = {
    "abstract",
    "caption",
    "entry",
    "item",
    "listitem",
    "para",
    "p",
    "subtitle",
    "term",
    "title",
}

JSON_STRUCTURAL_KEYS = {
    "tag",
    "node_type",
    "nodetype",
}


def normalize_text(value: Any) -> str:
    return " ".join(str(value if value is not None else "").split())


def _deduplicate(values: Iterable[str]) -> List[str]:
    result = []
    for value in values:
        text = normalize_text(value)
        if text and (not result or result[-1] != text):
            result.append(text)
    return result


def _local_name(tag: str) -> str:
    return tag.split("}")[-1].lower()


def extract_xml_texts(root) -> List[str]:
    paragraphs = []
    for element in root.iter():
        tag = _local_name(element.tag)
        if tag not in XML_BLOCK_TAGS:
            continue

        has_nested_block = any(_local_name(child.tag) in XML_BLOCK_TAGS for child in element)
        if has_nested_block:
            continue

        text = normalize_text("".join(element.itertext()))
        if text:
            paragraphs.append(text)

    if paragraphs:
        return _deduplicate(paragraphs)

    fallback = []
    for element in root.iter():
        if len(element) == 0:
            text = normalize_text(element.text)
            if text:
                fallback.append(text)
    return _deduplicate(fallback)


def extract_json_texts(data: Any) -> List[str]:
    values = []

    def walk(value: Any, key: str = "") -> None:
        normalized_key = key.replace("-", "_").lower()
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                walk(child_value, str(child_key))
            return
        if isinstance(value, list):
            for item in value:
                walk(item, key)
            return
        if normalized_key in JSON_STRUCTURAL_KEYS:
            return
        if value is None:
            values.append("null")
            return
        if isinstance(value, bool):
            values.append("true" if value else "false")
            return
        if isinstance(value, (str, int, float)):
            text = normalize_text(value)
            if text:
                values.append(text)

    walk(data)
    return _deduplicate(values)


def build_text_html(title: str, paragraphs: Iterable[str]) -> str:
    items = list(paragraphs)
    body = "\n".join(f"<p>{html.escape(item)}</p>" for item in items)
    if not body:
        body = "<p>No text content found.</p>"

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    @page {{ margin: 14mm; }}
    body {{
      margin: 0;
      color: #172033;
      background: #ffffff;
      font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      font-size: 16px;
      line-height: 1.75;
      overflow-wrap: anywhere;
    }}
    main {{ max-width: 980px; margin: 0 auto; padding: 28px 34px; }}
    h1 {{ margin: 0 0 24px; font-size: 24px; font-weight: 600; }}
    p {{ margin: 0 0 14px; white-space: pre-wrap; }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(title)}</h1>
    {body}
  </main>
</body>
</html>"""


def _display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1 for char in text)


def _wrap_text(text: str, max_width: int) -> List[str]:
    lines = []
    current = []
    current_width = 0
    for char in text:
        width = 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        if current and current_width + width > max_width:
            lines.append("".join(current))
            current = []
            current_width = 0
        current.append(char)
        current_width += width
    if current:
        lines.append("".join(current))
    return lines or [""]


def build_text_svg(title: str, paragraphs: Iterable[str], width: int = 1200) -> str:
    text_lines = []
    for paragraph in paragraphs:
        text_lines.extend(_wrap_text(paragraph, 76))
        text_lines.append("")
    if text_lines and not text_lines[-1]:
        text_lines.pop()
    if not text_lines:
        text_lines = ["No text content found."]

    padding = 40
    title_height = 54
    line_height = 30
    height = max(240, padding * 2 + title_height + len(text_lines) * line_height)
    nodes = []
    for index, line in enumerate(text_lines):
        y = padding + title_height + (index + 1) * line_height
        nodes.append(
            f'<text x="{padding}" y="{y}" font-size="18" fill="#172033">{html.escape(line)}</text>'
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <g font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">
    <text x="{padding}" y="{padding + 28}" font-size="26" font-weight="600" fill="#111827">{html.escape(title)}</text>
    {''.join(nodes)}
  </g>
</svg>"""
