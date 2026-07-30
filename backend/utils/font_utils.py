from __future__ import annotations

import os
from typing import Iterable, Optional


CJK_FONT_PATHS = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyh.ttf",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
)

LATIN_FONT_PATHS = (
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def existing_font_paths(extra_paths: Optional[Iterable[str]] = None):
    for path in list(extra_paths or []) + list(CJK_FONT_PATHS) + list(LATIN_FONT_PATHS):
        if path and os.path.exists(path):
            yield path


def get_pil_font(size: int):
    from PIL import ImageFont

    for path in existing_font_paths():
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def register_reportlab_cjk_font(font_name: str = "DocConverterCJK") -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont

    for path in existing_font_paths():
        for kwargs in ({}, {"subfontIndex": 0}):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path, **kwargs))
                return font_name
            except Exception:
                continue

    fallback_name = "STSong-Light"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(fallback_name))
        return fallback_name
    except Exception:
        return "Helvetica"
