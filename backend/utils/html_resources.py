from __future__ import annotations

import base64
import binascii
import ipaddress
import mimetypes
import socket
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _is_public_host(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def _read_data_uri(src: str) -> Optional[tuple[bytes, str]]:
    header, separator, payload = src.partition(",")
    if not separator:
        return None

    media_type = header[5:].split(";", 1)[0].strip().lower() or "application/octet-stream"
    if not media_type.startswith("image/"):
        return None

    try:
        if ";base64" in header.lower():
            data = base64.b64decode(payload, validate=True)
        else:
            data = unquote(payload).encode("utf-8")
    except (binascii.Error, ValueError):
        return None

    if not data or len(data) > MAX_IMAGE_BYTES:
        return None
    return data, media_type


def _read_local_image(src: str, base_path: str) -> Optional[tuple[bytes, str]]:
    base_dir = Path(base_path).resolve().parent
    parsed = urlparse(src)
    raw_path = unquote(parsed.path if parsed.scheme == "file" else src.split("#", 1)[0].split("?", 1)[0])
    candidate = (base_dir / raw_path).resolve()

    try:
        candidate.relative_to(base_dir)
    except ValueError:
        return None

    if not candidate.is_file():
        return None
    data = candidate.read_bytes()
    if not data or len(data) > MAX_IMAGE_BYTES:
        return None

    media_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    if not media_type.startswith("image/"):
        return None
    return data, media_type


def _read_remote_image(src: str, timeout: int) -> Optional[tuple[bytes, str]]:
    parsed = urlparse(src)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if not _is_public_host(parsed.hostname):
        return None

    request = Request(src, headers={"User-Agent": "KunqiongAI-Doc-Converter/1.0"})
    with urlopen(request, timeout=timeout) as response:
        media_type = response.headers.get_content_type()
        if not media_type.startswith("image/"):
            return None
        data = response.read(MAX_IMAGE_BYTES + 1)
    if not data or len(data) > MAX_IMAGE_BYTES:
        return None
    return data, media_type


def resolve_html_image(src: str, base_path: str | None = None, timeout: int = 10) -> Optional[tuple[bytes, str]]:
    src = str(src or "").strip()
    if not src:
        return None

    if src.startswith("data:"):
        return _read_data_uri(src)

    parsed = urlparse(src)
    if parsed.scheme in {"http", "https"}:
        return _read_remote_image(src, timeout)

    if base_path:
        return _read_local_image(src, base_path)

    return None


def image_data_uri(image_bytes: bytes, media_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def inline_soup_images(soup, base_path: str | None = None) -> int:
    """Inline resolvable <img> sources so single-file exports keep images."""
    inlined_count = 0
    for image in soup.find_all("img"):
        src = str(image.get("src") or "").strip()
        if not src or src.startswith("data:"):
            continue

        resolved = resolve_html_image(src, base_path=base_path)
        if not resolved:
            continue

        image_bytes, media_type = resolved
        image["src"] = image_data_uri(image_bytes, media_type)
        inlined_count += 1
    return inlined_count
