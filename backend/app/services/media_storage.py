from __future__ import annotations

import asyncio
import json
import secrets
import shutil
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.models.media_asset import MediaKind

Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard

_EXT = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp",
    "video/mp4": ".mp4", "video/webm": ".webm",
}
_CHUNK = 1024 * 1024


@dataclass
class StoredMedia:
    stored_name: str
    kind: MediaKind
    content_type: str
    size_bytes: int
    width: int
    height: int
    duration: Optional[Decimal]


def _sniff(head: bytes) -> Optional[str]:
    if head.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if head.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"): return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP": return "image/webp"
    if head[4:8] == b"ftyp": return "video/mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"): return "video/webm"
    return None


def _probe_image(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            return im.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Not a valid image file")


def _probe_video(path: Path) -> Optional[tuple[int, int, Decimal]]:
    if shutil.which("ffprobe") is None:
        return None
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=20, check=True,
        ).stdout
        data = json.loads(out)
        s = data["streams"][0]
        return int(s["width"]), int(s["height"]), Decimal(str(round(float(data["format"]["duration"]), 2)))
    except Exception:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Not a valid video file")


async def save_upload(
    file: UploadFile, fallback_size: tuple[Optional[int], Optional[int]] = (None, None)
) -> StoredMedia:
    head = await file.read(32)
    content_type = _sniff(head)
    if content_type is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Unsupported file. Use PNG, JPEG, GIF, WebP, MP4 or WebM.",
        )
    kind = MediaKind.VIDEO if content_type.startswith("video/") else MediaKind.IMAGE
    limit = (settings.media_max_video_mb if kind == MediaKind.VIDEO else settings.media_max_image_mb) * 1024 * 1024

    settings.media_dir.mkdir(parents=True, exist_ok=True)
    stored_name = secrets.token_hex(16) + _EXT[content_type]
    path = settings.media_dir / stored_name

    size = 0
    try:
        with path.open("wb") as out:
            chunk = head
            while chunk:
                size += len(chunk)
                if size > limit:
                    raise HTTPException(
                        status.HTTP_413_CONTENT_TOO_LARGE,
                        f"File too large (max {limit // 1024 // 1024} MB for {kind.value}s)",
                    )
                await asyncio.to_thread(out.write, chunk)
                chunk = await file.read(_CHUNK)

        duration = None
        if kind == MediaKind.IMAGE:
            width, height = await asyncio.to_thread(_probe_image, path)
        else:
            probed = await asyncio.to_thread(_probe_video, path)
            if probed:
                width, height, duration = probed
                if duration > settings.media_max_video_seconds:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        f"Video too long (max {settings.media_max_video_seconds}s)",
                    )
            elif fallback_size[0] and fallback_size[1]:
                width, height = fallback_size
            else:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Server can't read video size; provide width and height",
                )
    except Exception:
        path.unlink(missing_ok=True)
        raise

    return StoredMedia(stored_name, kind, content_type, size, width, height, duration)


def delete_file(stored_name: str) -> None:
    (settings.media_dir / stored_name).unlink(missing_ok=True)
