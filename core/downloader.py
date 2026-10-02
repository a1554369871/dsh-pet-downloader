# -*- coding: utf-8 -*-
"""文件下载（urllib + 可选 certifi SSL；支持进度回调与取消）。"""
from __future__ import annotations

import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from threading import Event
from typing import Callable

CHUNK = 64 * 1024


class DownloadError(RuntimeError):
    pass


class DownloadCancelled(DownloadError):
    pass


def _ssl_context():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def download_file(
    url: str,
    dest: Path,
    *,
    progress: Callable[[int, int], None] | None = None,
    cancel: Event | None = None,
    timeout: float = 30.0,
) -> Path:
    """把 url 下载到 dest（原子写入 .part 后改名）。"""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    request = urllib.request.Request(
        url, headers={"User-Agent": "dsh-pet-downloader", "Accept": "*/*"}
    )
    try:
        response = urllib.request.urlopen(
            request, timeout=timeout, context=_ssl_context()
        )
    except urllib.error.HTTPError as exc:
        raise DownloadError(f"HTTP {exc.code}：{url}") from exc
    except urllib.error.URLError as exc:
        raise DownloadError(f"网络连接失败：{exc.reason}") from exc
    except OSError as exc:
        raise DownloadError(f"网络请求失败：{exc}") from exc

    total = 0
    try:
        length = response.headers.get("Content-Length")
        total = int(length) if length and length.isdigit() else 0
    except Exception:
        total = 0

    written = 0
    try:
        with open(part, "wb") as handle:
            while True:
                if cancel is not None and cancel.is_set():
                    raise DownloadCancelled("下载已取消")
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                handle.write(chunk)
                written += len(chunk)
                if progress is not None:
                    progress(written, total)
    except DownloadCancelled:
        _safe_remove(part)
        raise
    except OSError as exc:
        _safe_remove(part)
        raise DownloadError(f"写入失败：{exc}") from exc
    finally:
        try:
            response.close()
        except Exception:
            pass

    if total and written < total:
        _safe_remove(part)
        raise DownloadError(f"下载不完整（{written}/{total} 字节）")
    try:
        os.replace(part, dest)
    except OSError as exc:
        _safe_remove(part)
        raise DownloadError(f"保存文件失败：{exc}") from exc
    return dest


def _safe_remove(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
