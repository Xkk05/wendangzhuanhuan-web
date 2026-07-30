from __future__ import annotations

import re

from bs4 import BeautifulSoup, Comment


HIDDEN_STYLE_PATTERN = re.compile(r"(?:display\s*:\s*none|visibility\s*:\s*hidden)", re.IGNORECASE)
HIDDEN_RULE_PATTERN = re.compile(
    r"([^{}]+)\{[^{}]*(?:display\s*:\s*none|visibility\s*:\s*hidden)[^{}]*\}",
    re.IGNORECASE,
)


def prepare_content_soup(html_content: str, options: dict | None = None) -> BeautifulSoup:
    options = options or {}
    soup = BeautifulSoup(html_content, "html.parser")

    hidden_selectors = []
    for style in soup.find_all("style"):
        for match in HIDDEN_RULE_PATTERN.finditer(style.get_text(" ")):
            hidden_selectors.extend(selector.strip() for selector in match.group(1).split(",") if selector.strip())
    for selector in hidden_selectors:
        try:
            for element in soup.select(selector):
                element.decompose()
        except Exception:
            continue

    for element in list(soup.find_all(True)):
        style = str(element.get("style") or "")
        if (
            element.has_attr("hidden")
            or str(element.get("aria-hidden") or "").lower() == "true"
            or (element.name == "input" and str(element.get("type") or "").lower() == "hidden")
            or HIDDEN_STYLE_PATTERN.search(style)
        ):
            element.decompose()

    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    for element in soup.find_all(["script", "style", "noscript", "template"]):
        element.decompose()

    if options.get("remove_empty_tags"):
        for element in reversed(soup.find_all(True)):
            if element.name not in {"html", "head", "body", "img", "br", "hr"}:
                if not element.get_text(strip=True) and not element.find(True):
                    element.decompose()
    return soup


def soup_text(soup: BeautifulSoup) -> str:
    lines = [line.strip() for line in soup.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line)
