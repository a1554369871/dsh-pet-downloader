# -*- coding: utf-8 -*-
"""可选 AI 配置：写 dsh-pet 的 config.json + 系统钥匙串，并提供连接测试。

密钥优先写入系统钥匙串（与 dsh-pet ``SecretStore`` 相同的服务名 / 账号），
同时在 config.json 里写一份 ``api_key`` 作为首次运行的兜底（dsh-pet 首次保存
设置后会剔除明文，此时以钥匙串为准）。
"""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from . import site_config

DEFAULT_CHAT = {
    "enabled": True,
    "active_provider": "openai-main",
    "default_system_prompt": "你是一只可爱的桌面宠物，请用自然、友善的中文和用户交流。",
    "history_message_limit": 40,
    "history_char_limit": 24000,
    "providers": {
        "openai-main": {
            "name": "DeepSeek",
            "base_url": site_config.DEFAULT_BASE_URL,
            "chat_path": "/v1/chat/completions",
            "model": site_config.DEFAULT_MODEL,
            "api_key_ref": site_config.KEYRING_REF,
            "api_key": "",
            "timeout": 60.0,
            "temperature": 0.7,
            "max_tokens": 2048,
        }
    },
}


def config_path(data_dir: Path, variant_data_dir: str) -> Path:
    return Path(data_dir) / variant_data_dir / "config.json"


def write_ai_config(
    data_dir: Path,
    variant_data_dir: str,
    *,
    base_url: str,
    model: str,
    api_key: str,
    provider_name: str = "DeepSeek",
) -> Path:
    """合并写入 AI 配置，返回 config.json 路径。"""
    path = config_path(data_dir, variant_data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, ValueError):
            data = {}
    data["version"] = 4
    chat = data.get("chat")
    if not isinstance(chat, dict):
        chat = {}
    providers = chat.get("providers")
    if not isinstance(providers, dict) or not providers:
        providers = json.loads(json.dumps(DEFAULT_CHAT["providers"]))
    provider = providers.get("openai-main")
    if not isinstance(provider, dict):
        provider = json.loads(json.dumps(DEFAULT_CHAT["providers"]["openai-main"]))
    provider["name"] = str(provider_name or "DeepSeek").strip() or "DeepSeek"
    provider["base_url"] = str(base_url or site_config.DEFAULT_BASE_URL).strip()
    provider["model"] = str(model or site_config.DEFAULT_MODEL).strip()
    provider["api_key_ref"] = site_config.KEYRING_REF
    provider["api_key"] = str(api_key or "")
    providers["openai-main"] = provider
    chat["providers"] = providers
    chat.setdefault("enabled", True)
    chat.setdefault("active_provider", "openai-main")
    chat.setdefault("default_system_prompt", DEFAULT_CHAT["default_system_prompt"])
    chat.setdefault("history_message_limit", 40)
    chat.setdefault("history_char_limit", 24000)
    data["chat"] = chat
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def store_keyring(api_key: str) -> bool:
    """把 API Key 写入系统钥匙串（不可用时返回 False）。"""
    if not api_key:
        return False
    try:
        import keyring

        keyring.set_password(site_config.KEYRING_SERVICE, site_config.KEYRING_REF, api_key)
        return True
    except Exception:
        return False


def normalize_chat_endpoint(base_url: str, chat_path: str = "/v1/chat/completions") -> str:
    base = str(base_url or "").strip().rstrip("/")
    path = str(chat_path or "/v1/chat/completions").strip()
    if not path.startswith("/"):
        path = "/" + path
    if base.endswith("/chat/completions"):
        return base
    if path == "/v1/chat/completions" and re.search(r"/v\d+$", base):
        return base + "/chat/completions"
    return base + path


def _ssl_context(verify: bool = True):
    if not verify:
        return ssl._create_unverified_context()
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def test_connection(
    base_url: str, model: str, api_key: str, *, timeout: float = 10.0
) -> tuple[bool, str]:
    """发送最小请求验证配置可用，返回 (ok, message)。"""
    endpoint = normalize_chat_endpoint(base_url)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=timeout, context=_ssl_context(True)
        ) as response:
            response.read(2048)
            return True, f"连接成功（HTTP {response.status}）"
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", "replace")
        message = _safe_detail(detail)
        if exc.code in (401, 403):
            return False, f"认证失败（HTTP {exc.code}）：{message}"
        if exc.code == 402:
            return False, f"余额不足（HTTP 402）：{message}"
        return False, f"请求失败（HTTP {exc.code}）：{message}"
    except urllib.error.URLError as exc:
        return False, f"网络连接失败：{exc.reason}"
    except OSError as exc:
        return False, f"网络请求失败：{exc}"


def _safe_detail(raw: str) -> str:
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("error"), dict):
            return str(data["error"].get("message", "请求失败"))
    except Exception:
        pass
    return " ".join(raw.split())[:300] or "请求失败"
