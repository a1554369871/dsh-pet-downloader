# -*- coding: utf-8 -*-
"""下载器核心逻辑单测（不依赖网络与图形界面）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ai_presets, api_config, installer, releases, site_config  # noqa: E402


def test_version_helpers():
    assert site_config.version_tuple("1.0.7.0") == (1, 0, 7, 0)
    assert site_config.supports_portable_data("1.0.7.0") is True
    assert site_config.supports_portable_data("1.0.6.7") is False
    assert site_config.supports_portable_data("1.0.10.0") is True


def test_resolve_assets():
    manifest = {"version": site_config.VERSION, "release_base": site_config.RELEASE_BASE, "assets": {}}
    name, url = releases.resolve("chat", "zip", manifest)
    assert name == "dsh-pet-standalone-webm-chat-portable.zip"
    assert url.endswith(name)
    name, url = releases.resolve("plain", "setup", manifest)
    assert name == "dsh-pet-standalone-webm-setup.exe"
    assert url.endswith(name)


def test_drive_defaults_use_install_data(tmp_path):
    from core import drives

    assert drives.data_dir_for(tmp_path) == tmp_path / "data"
    default = drives.default_install_dir("dsh-pet-standalone-webm-chat")
    assert default.name == "dsh-pet-standalone-webm-chat"


def test_normalize_chat_endpoint():
    assert api_config.normalize_chat_endpoint("https://api.deepseek.com") == (
        "https://api.deepseek.com/v1/chat/completions"
    )
    assert api_config.normalize_chat_endpoint("https://api.deepseek.com/v1") == (
        "https://api.deepseek.com/v1/chat/completions"
    )
    full = "https://host/v1/chat/completions"
    assert api_config.normalize_chat_endpoint(full) == full


def test_ai_presets_default_and_lookup():
    default = ai_presets.default()
    assert default.key == ai_presets.DEFAULT_KEY
    assert ai_presets.PROVIDERS[0].key == ai_presets.DEFAULT_KEY
    assert default.base_url == "https://api.deepseek.com"
    glm = ai_presets.get("glm")
    assert glm.name == "智谱 GLM"
    assert glm.base_url.endswith("/api/paas/v4")
    # 未知 key 回退到默认
    assert ai_presets.get("nope").key == ai_presets.DEFAULT_KEY
    # 自定义预设地址/模型为空
    assert ai_presets.get("custom").base_url == ""


def test_write_ai_config_records_provider_name(tmp_path):
    data_dir = tmp_path / "data"
    path = api_config.write_ai_config(
        data_dir,
        "dsh-pet-standalone-webm-chat",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        model="glm-4.6",
        api_key="k",
        provider_name="智谱 GLM",
    )
    provider = json.loads(path.read_text(encoding="utf-8"))["chat"]["providers"]["openai-main"]
    assert provider["name"] == "智谱 GLM"
    assert provider["model"] == "glm-4.6"


def test_write_ai_config_creates_and_merges(tmp_path):
    data_dir = tmp_path / "data"
    path = api_config.write_ai_config(
        data_dir,
        "dsh-pet-standalone-webm-chat",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        api_key="sk-test",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    provider = payload["chat"]["providers"]["openai-main"]
    assert provider["base_url"] == "https://api.deepseek.com"
    assert provider["model"] == "deepseek-v4-flash"
    assert provider["api_key"] == "sk-test"
    assert provider["api_key_ref"] == "provider/openai-main"
    assert payload["version"] == 4

    # 二次写入应保留既有其它字段
    payload["custom_key"] = 123
    path.write_text(json.dumps(payload), encoding="utf-8")
    api_config.write_ai_config(
        data_dir,
        "dsh-pet-standalone-webm-chat",
        base_url="https://example.com/v1",
        model="m1",
        api_key="",
    )
    merged = json.loads(path.read_text(encoding="utf-8"))
    assert merged["custom_key"] == 123
    assert merged["chat"]["providers"]["openai-main"]["base_url"] == "https://example.com/v1"
    assert merged["chat"]["providers"]["openai-main"]["api_key"] == ""


def test_marker_and_pointer(tmp_path, monkeypatch):
    install_dir = tmp_path / "install"
    data_dir = install_dir / "data"
    marker = installer.write_marker(install_dir, data_dir)
    assert marker.read_text(encoding="utf-8") == str(data_dir)
    assert marker.name == site_config.MARKER_NAME

    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    pointer = installer.write_pointer(data_dir)
    assert pointer.read_text(encoding="utf-8") == str(data_dir)
    assert pointer == tmp_path / "appdata" / "dsh-pet" / "data-root.txt"


def test_uninstall_bat_and_user_data_scan(tmp_path):
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    bat = installer.write_uninstall_bat(install_dir, "chat")
    text = bat.read_text(encoding="utf-8")
    assert "--uninstall-cleanup" in text
    assert "dsh-pet-standalone-webm-chat.exe" in text

    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "app.exe").write_text("x", encoding="utf-8")
    assert installer.find_user_data(clean) == []

    (clean / "config.json").write_text("{}", encoding="utf-8")
    (clean / "sessions").mkdir()
    found = installer.find_user_data(clean)
    assert any("config.json" in item for item in found)
    assert any("sessions" in item for item in found)


def test_fetch_manifest_falls_back_offline(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    manifest = releases.fetch_manifest(timeout=0.1)
    assert manifest["source"] == "embedded"
    assert manifest["version"] == site_config.VERSION
