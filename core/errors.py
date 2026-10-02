# -*- coding: utf-8 -*-
"""把安装/下载错误翻译成对用户友好的分类与处理建议。"""
from __future__ import annotations

from . import site_config

KIND_SSL = "ssl"
KIND_HTTP = "http"
KIND_NETWORK = "network"
KIND_UNKNOWN = "unknown"


def classify_error(message: str) -> tuple[str, str]:
    """返回 (kind, hint)。hint 为给用户看的处理建议。"""
    text = str(message or "")
    upper = text.upper()

    if "CERTIFICATE_VERIFY_FAILED" in upper or "SSL:" in upper or "CERTIFICATE" in upper:
        return KIND_SSL, (
            "检测到 TLS 证书校验失败，通常是网络代理 / 加速器（如 Watt Toolkit、VPN）"
            "或安全软件拦截了证书。\n"
            "可尝试：① 关闭加速器 / 代理后重试；② 直接使用「离线完整版」安装（推荐）。"
        )
    if "403" in text or "404" in text or "NOT FOUND" in upper or "FORBIDDEN" in upper:
        return KIND_HTTP, (
            "在线源仓库当前未公开或无权访问（403/404）。\n"
            "普通用户请改用「离线完整版」，它内置安装包、无需联网。"
        )
    if "超时" in text or "TIMED OUT" in upper or "TIMEOUT" in upper:
        return KIND_NETWORK, "网络请求超时。请检查网络后重试，或改用「离线完整版」。"
    if "网络" in text or "CONNECTION" in upper or "URLError" in text:
        return KIND_NETWORK, "网络连接失败。请检查网络后重试，或改用「离线完整版」。"
    return KIND_UNKNOWN, "安装失败。可重试，或改用「离线完整版」安装。"


def offline_hint() -> str:
    return site_config.OFFLINE_DOWNLOAD_URL
