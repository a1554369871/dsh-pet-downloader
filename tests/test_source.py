# -*- coding: utf-8 -*-
"""在线源解析优先级测试。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import source  # noqa: E402


def test_source_file_loaded(tmp_path, monkeypatch):
    monkeypatch.delenv(source.SOURCE_ENV_VAR, raising=False)
    (tmp_path / source.SOURCE_FILE_NAME).write_text(
        json.dumps({"release_base": "https://mirror/base"}), encoding="utf-8"
    )
    merged = source.resolve(base=tmp_path)
    assert merged["release_base"] == "https://mirror/base"


def test_override_beats_file(tmp_path, monkeypatch):
    monkeypatch.delenv(source.SOURCE_ENV_VAR, raising=False)
    (tmp_path / source.SOURCE_FILE_NAME).write_text(
        json.dumps({"manifest_url": "file-url"}), encoding="utf-8"
    )
    merged = source.resolve({"manifest_url": "override-url"}, base=tmp_path)
    assert merged["manifest_url"] == "override-url"


def test_env_beats_all(tmp_path, monkeypatch):
    (tmp_path / source.SOURCE_FILE_NAME).write_text(
        json.dumps({"manifest_url": "file-url"}), encoding="utf-8"
    )
    monkeypatch.setenv(source.SOURCE_ENV_VAR, json.dumps({"manifest_url": "env-url"}))
    merged = source.resolve({"manifest_url": "override-url"}, base=tmp_path)
    assert merged["manifest_url"] == "env-url"


def test_env_plain_url(tmp_path, monkeypatch):
    monkeypatch.setenv(source.SOURCE_ENV_VAR, "https://host/update.json")
    merged = source.resolve(base=tmp_path)
    assert merged["manifest_url"] == "https://host/update.json"


def test_empty_source(tmp_path, monkeypatch):
    monkeypatch.delenv(source.SOURCE_ENV_VAR, raising=False)
    assert source.resolve(base=tmp_path) == {}
