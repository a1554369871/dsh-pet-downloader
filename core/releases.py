# -*- coding: utf-8 -*-
"""解析 dsh-pet 发布版本与资产直链。

默认读取官方仓库的 ``update.json``，也可通过 ``source`` 指定自建清单/镜像；
网络不可用时回退到 ``site_config`` 内嵌常量，保证离线/内网环境也能工作。
"""
from __future__ import annotations

import json
import urllib.request

from . import source as source_mod
from . import site_config


def _ssl_context():
    try:
        import certifi
        import ssl

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def _embedded_manifest(source_cfg: dict | None = None) -> dict:
    source_cfg = source_cfg or {}
    assets = dict(site_config.ASSETS)
    overrides = source_cfg.get("assets")
    if isinstance(overrides, dict):
        assets.update({str(k): str(v) for k, v in overrides.items()})
    return {
        "version": site_config.VERSION,
        "release_base": source_cfg.get("release_base") or site_config.RELEASE_BASE,
        "assets": assets,
        "source": "embedded",
    }


def fetch_manifest(timeout: float = 8.0, source: dict | None = None) -> dict:
    """获取版本清单；失败时返回内嵌清单。"""
    source_cfg = source if source is not None else source_mod.resolve()
    manifest_url = str(source_cfg.get("manifest_url") or "").strip() or site_config.UPDATE_JSON_URL
    try:
        request = urllib.request.Request(
            manifest_url,
            headers={"User-Agent": "dsh-pet-downloader", "Accept": "application/json"},
        )
        context = _ssl_context()
        kwargs = {"timeout": timeout}
        if context is not None:
            kwargs["context"] = context
        with urllib.request.urlopen(request, **kwargs) as response:
            raw = json.loads(response.read().decode("utf-8", "replace"))
        version = str(raw.get("version") or "").strip()
        assets = raw.get("assets")
        if version and isinstance(assets, dict) and assets:
            release_base = (
                str(source_cfg.get("release_base") or "").strip()
                or f"{site_config.REPO}/releases/download/v{version}"
            )
            merged_assets = {str(k): str(v) for k, v in assets.items()}
            overrides = source_cfg.get("assets")
            if isinstance(overrides, dict):
                merged_assets.update({str(k): str(v) for k, v in overrides.items()})
            return {
                "version": version,
                "release_base": release_base,
                "assets": merged_assets,
                "source": "remote",
            }
    except Exception:
        pass
    return _embedded_manifest(source_cfg)


def asset_url(manifest: dict, key: str) -> str | None:
    """按内嵌键名取得下载直链（远端清单按文件名匹配）。"""
    filename = site_config.ASSETS.get(key)
    if not filename:
        return None
    assets = manifest.get("assets") or {}
    url = assets.get(filename)
    if url:
        return str(url)
    base = manifest.get("release_base") or site_config.RELEASE_BASE
    return f"{base}/{filename}"


def asset_filename(key: str) -> str | None:
    return site_config.ASSETS.get(key)


def resolve(variant_key: str, method: str, manifest: dict) -> tuple[str, str]:
    """返回 (文件名, 直链)。method 为 ``zip`` 或 ``setup``。"""
    variant = site_config.VARIANTS[variant_key]
    key = variant["setup_key"] if method == "setup" else variant["zip_key"]
    filename = asset_filename(key)
    url = asset_url(manifest, key)
    if not filename or not url:
        raise ValueError(f"未知资产: {variant_key}/{method}")
    return filename, url
