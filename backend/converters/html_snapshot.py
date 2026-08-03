from __future__ import annotations

import os
import re
import tempfile
from typing import Any


VISUAL_TAGS = {"canvas", "svg", "video", "object", "embed"}
INTERACTIVE_TAGS = {"button", "input", "select", "textarea"}
VISUAL_STYLE_PATTERN = re.compile(
    r"(?:background(?:-color|-image)?|border|box-shadow|"
    r"position\s*:|display\s*:\s*(?:flex|grid|inline-flex)|"
    r"(?:min-|max-)?(?:width|height)\s*:|transform\s*:|animation\s*:)",
    re.IGNORECASE,
)


def should_include_rendered_snapshot(soup: Any, options: dict | None = None) -> bool:
    """Return true when static text extraction would miss a rendered UI surface."""
    options = options or {}
    setting = str(options.get("include_rendered_snapshot") or "auto").strip().lower()
    if setting in {"false", "0", "no", "off", "never"}:
        return False
    if setting in {"true", "1", "yes", "on", "always"}:
        return True

    root = soup.body or soup
    if root.find(VISUAL_TAGS) or root.find(INTERACTIVE_TAGS):
        return True

    for element in root.find_all(style=True):
        style = str(element.get("style") or "")
        if VISUAL_STYLE_PATTERN.search(style):
            return True

    for style in soup.find_all("style"):
        if VISUAL_STYLE_PATTERN.search(style.get_text(" ")):
            return True

    return False


def render_html_snapshot(input_path: str, output_dir: str, options: dict | None = None) -> bytes:
    """Render HTML to a temporary PNG and return the image bytes."""
    from .html_to_image import HtmlToImageConverter

    os.makedirs(output_dir, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        prefix="html_render_snapshot_",
        suffix=".png",
        dir=output_dir,
        delete=False,
    )
    temp_path = temp_file.name
    temp_file.close()

    try:
        snapshot_options = dict(options or {})
        snapshot_options["code_mode"] = False
        HtmlToImageConverter().convert(input_path, temp_path, **snapshot_options)
        with open(temp_path, "rb") as image_file:
            return image_file.read()
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
