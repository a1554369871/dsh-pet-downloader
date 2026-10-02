# -*- coding: utf-8 -*-
"""内置离线载荷（payload）探测测试。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import payload, site_config  # noqa: E402


def _write_payload(base: Path) -> None:
    pdir = payload.payload_dir(base)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "dsh-pet-standalone-webm-chat-setup.exe").write_bytes(b"chat")
    (pdir / "dsh-pet-standalone-webm-setup.exe").write_bytes(b"plain")
    manifest = {
        "version": "1.0.7.0",
        "assets": {
            "winChatSetup": {"file": "dsh-pet-standalone-webm-chat-setup.exe", "size": 4},
            "winSetup": {"file": "dsh-pet-standalone-webm-setup.exe", "size": 5},
        },
    }
    (pdir / payload.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")


def test_payload_detection(tmp_path):
    _write_payload(tmp_path)
    assert payload.bundled_version(tmp_path) == "1.0.7.0"
    assert payload.has_variant("chat", tmp_path)
    assert payload.has_variant("plain", tmp_path)
    assert set(payload.available_variants(tmp_path)) == {"chat", "plain"}
    assert payload.asset_path("chat", tmp_path).name == "dsh-pet-standalone-webm-chat-setup.exe"
    assert payload.is_offline(tmp_path)


def test_payload_absent(tmp_path):
    assert payload.load_manifest(tmp_path) == {}
    assert payload.available_variants(tmp_path) == []
    assert payload.asset_path("chat", tmp_path) is None
    assert not payload.is_offline(tmp_path)


def test_payload_filename_fallback(tmp_path):
    pdir = payload.payload_dir(tmp_path)
    pdir.mkdir(parents=True, exist_ok=True)
    name = site_config.ASSETS["winChatSetup"]
    (pdir / name).write_bytes(b"x")
    # 没有 manifest 时按约定文件名探测
    assert payload.has_variant("chat", tmp_path)
    assert payload.asset_path("chat", tmp_path).name == name
