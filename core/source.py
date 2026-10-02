# -*- coding: utf-8 -*-
"""在线下载源解析：默认官方 dsh-pet，可通过环境变量 / source.json / 向导覆盖。

优先级（高 → 低）：
1. 环境变量 ``DSH_PET_SOURCE``（可为 JSON 对象，或单个 manifest URL）
2. exe 同目录 ``source.json``
3. 向导高级项（本次会话传入的 override）
4. 官方默认（``site_config``）

source 字段（全部可选）：
- ``manifest_url``：版本清单 JSON 地址（结构同 dsh-pet update.json）
- ``release_base``：资产直链前缀
- ``assets``：``{文件名: 直链}`` 覆盖
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SOURCE_ENV_VAR = "DSH_PET_SOURCE"
SOURCE_FILE_NAME = "source.json"


def _app_base() -> Path:
    if getattr(sys, "frozen", False):
        try:
            return Path(sys.executable).resolve().parent
        except OSError:
            return Path.cwd()
    return Path(__file__).resolve().parent.parent


def source_file_path(base: Path | None = None) -> Path:
    return (base or _app_base()) / SOURCE_FILE_NAME


def load_source_file(base: Path | None = None) -> dict:
    try:
        path = source_file_path(base)
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {k: v for k, v in data.items() if v}
    except (OSError, ValueError):
        pass
    return {}


def _clean(mapping: dict) -> dict:
    return {str(k): v for k, v in mapping.items() if v not in (None, "", {}, [])}


def resolve(override: dict | None = None, base: Path | None = None) -> dict:
    """合并得到最终下载源配置（缺省时返回空 dict，表示官方默认）。"""
    result: dict = {}
    result.update(_clean(load_source_file(base)))
    if override:
        result.update(_clean(override))

    env = os.environ.get(SOURCE_ENV_VAR, "").strip()
    if env:
        try:
            data = json.loads(env)
            if isinstance(data, dict):
                result.update(_clean(data))
            else:
                result["manifest_url"] = env
        except ValueError:
            result["manifest_url"] = env
    return result
