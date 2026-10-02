# -*- coding: utf-8 -*-
"""下载器站点常量：版本、下载直链、网站入口、marker 约定。

版本更新时同步 ``pet/__init__.py``、``dsh-pet/update.json`` 与本文件即可。
"""
from __future__ import annotations

APP_NAME = "dsh-pet 下载器"
VERSION = "1.0.8.0"

# 支持「便携数据根」（数据跟随安装目录）的最低 dsh-pet 版本。
MIN_PORTABLE_DATA_VERSION = (1, 0, 7, 0)

REPO = "https://github.com/a1554369871/dsh-pet"
RELEASES_PAGE = f"{REPO}/releases"
RELEASE_BASE = f"{REPO}/releases/download/v{VERSION}"
# 运行时优先读它拿到最新版本与直链；失败回退本文件内嵌常量。
UPDATE_JSON_URL = (
    "https://raw.githubusercontent.com/a1554369871/dsh-pet/main/update.json"
)

# 网站入口（用户自行查看功能介绍）。
WEBSITE_GUIDE = "https://a1554369871.github.io/website/guide.html"
WEBSITE_HOME = "https://a1554369871.github.io/website/"
WEBSITE_DOWNLOAD = "https://a1554369871.github.io/website/download.html"

# 公开渠道：dsh-pet-downloader 仓库（匿名可访问），离线自包含包在此发布。
# 注意：dsh-pet 主仓库当前未公开，匿名在线安装会 403/404，故失败时引导到这里。
DOWNLOADER_REPO = "https://github.com/a1554369871/dsh-pet-downloader"
OFFLINE_RELEASES_PAGE = f"{DOWNLOADER_REPO}/releases"
OFFLINE_DOWNLOAD_URL = (
    f"{DOWNLOADER_REPO}/releases/latest/download/dsh-pet-downloader-offline.zip"
)

# 内嵌资产（与 update.json 的 assets 键一致）。
ASSETS = {
    "winChatSetup": "dsh-pet-standalone-webm-chat-setup.exe",
    "winChatZip": "dsh-pet-standalone-webm-chat-portable.zip",
    "winSetup": "dsh-pet-standalone-webm-setup.exe",
    "winZip": "dsh-pet-standalone-webm-portable.zip",
}
ASSET_SIZES = {
    "winChatSetup": "约 128 MB",
    "winChatZip": "约 156 MB",
    "winSetup": "约 128 MB",
    "winZip": "约 156 MB",
}

# 变体 → 数据目录名 / 内嵌产物键 / 可执行文件名。
VARIANTS = {
    "chat": {
        "label": "Chat 版（含 AI 对话）",
        "data_dir": "dsh-pet-standalone-webm-chat",
        "exe": "dsh-pet-standalone-webm-chat.exe",
        "setup_key": "winChatSetup",
        "zip_key": "winChatZip",
        "has_chat": True,
    },
    "plain": {
        "label": "无 Chat 版（只有桌宠）",
        "data_dir": "dsh-pet-standalone-webm",
        "exe": "dsh-pet-standalone-webm.exe",
        "setup_key": "winSetup",
        "zip_key": "winZip",
        "has_chat": False,
    },
}

# 数据根 marker / 全局指针文件名（与 pet/data_paths.py 保持一致）。
DATA_DIR_NAME = "data"
MARKER_NAME = "dsh-pet-data-root.txt"
POINTER_NAME = "data-root.txt"
POINTER_PARENT = "dsh-pet"

# keyring 服务名与账号（与 pet/chat/models.py SecretStore 保持一致）。
KEYRING_SERVICE = "dsh-pet-standalone"
KEYRING_REF = "provider/openai-main"

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"


def version_tuple(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in str(value or "").split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def supports_portable_data(version: str) -> bool:
    return version_tuple(version) >= MIN_PORTABLE_DATA_VERSION
