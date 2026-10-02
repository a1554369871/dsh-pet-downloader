# -*- coding: utf-8 -*-
"""内置离线载荷（payload）支持。

离线自包含版下载器把 dsh-pet 安装包放在 exe 同目录的 ``payload/`` 下，
并附一份 ``manifest.json`` 描述版本与各资产。存在对应变体时下载器可完全
离线安装，不再访问 dsh-pet 的下载路径。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import site_config

PAYLOAD_DIR_NAME = "payload"
MANIFEST_NAME = "manifest.json"


def _app_base() -> Path:
    """下载器所在目录：打包产物取 exe 同目录；源码运行取仓库根。"""
    if getattr(sys, "frozen", False):
        try:
            return Path(sys.executable).resolve().parent
        except OSError:
            return Path.cwd()
    return Path(__file__).resolve().parent.parent


def payload_dir(base: Path | None = None) -> Path:
    return (base or _app_base()) / PAYLOAD_DIR_NAME


def manifest_path(base: Path | None = None) -> Path:
    return payload_dir(base) / MANIFEST_NAME


def load_manifest(base: Path | None = None) -> dict:
    """读取 payload/manifest.json；不存在或损坏返回空 dict。"""
    try:
        path = manifest_path(base)
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass
    return {}


def bundled_version(base: Path | None = None) -> str:
    return str(load_manifest(base).get("version") or "").strip()


def asset_info(variant_key: str, base: Path | None = None) -> dict:
    """返回内置某变体的信息（{file,size,sha256}），无则空 dict。"""
    key = site_config.VARIANTS.get(variant_key, {}).get("setup_key")
    if not key:
        return {}
    assets = load_manifest(base).get("assets")
    if isinstance(assets, dict):
        info = assets.get(key)
        if isinstance(info, dict) and info.get("file"):
            if (payload_dir(base) / info["file"]).is_file():
                return info
    # 回退：按约定文件名探测
    filename = site_config.ASSETS.get(key)
    if filename and (payload_dir(base) / filename).is_file():
        return {"file": filename}
    return {}


def asset_path(variant_key: str, base: Path | None = None) -> Path | None:
    info = asset_info(variant_key, base)
    if not info:
        return None
    path = payload_dir(base) / str(info["file"])
    return path if path.is_file() else None


def has_variant(variant_key: str, base: Path | None = None) -> bool:
    return asset_path(variant_key, base) is not None


def available_variants(base: Path | None = None) -> list[str]:
    return [key for key in site_config.VARIANTS if has_variant(key, base)]


def is_offline(base: Path | None = None) -> bool:
    return bool(available_variants(base))
