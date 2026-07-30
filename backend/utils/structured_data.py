from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def scalar_to_text(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def flatten_json_values(data: Any) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if not value:
                rows.append((path or "$", "{}"))
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                walk(child, child_path)
            return
        if isinstance(value, list):
            if not value:
                rows.append((path or "$", "[]"))
            for index, child in enumerate(value, start=1):
                walk(child, f"{path}[{index}]" if path else f"[{index}]")
            return
        rows.append((path or "$", scalar_to_text(value)))

    walk(data, "")
    return rows


def flatten_xml_values(root) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    def local_name(tag: str) -> str:
        return tag.split("}")[-1]

    def clean_text(value: Any) -> str:
        return " ".join(str(value or "").split())

    def walk(element, path: str) -> None:
        for key, value in sorted(element.attrib.items()):
            rows.append((f"{path}.@{local_name(key)}", str(value)))

        children = list(element)
        text = clean_text(element.text)
        if text:
            rows.append((f"{path}.#text" if children else path, text))

        counts = Counter(local_name(child.tag) for child in children)
        indexes: Counter[str] = Counter()
        for child in children:
            name = local_name(child.tag)
            indexes[name] += 1
            suffix = f"[{indexes[name]}]" if counts[name] > 1 else ""
            walk(child, f"{path}.{name}{suffix}")
            tail = clean_text(child.tail)
            if tail:
                rows.append((f"{path}.#text[{indexes[name]}]", tail))

    root_name = local_name(root.tag)
    walk(root, root_name)
    return rows


def append_path_value_rows(worksheet, rows: Iterable[tuple[str, str]]) -> int:
    worksheet.append(["path", "value"])
    count = 0
    for path, value in rows:
        worksheet.append([path, value])
        count += 1
    return count
