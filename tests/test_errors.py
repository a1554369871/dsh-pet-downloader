# -*- coding: utf-8 -*-
"""错误分类（core.errors）测试。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import errors  # noqa: E402


def test_classify_ssl():
    msg = (
        "网络连接失败：[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
        "unable to get local issuer certificate (_ssl.c:1082)"
    )
    kind, hint = errors.classify_error(msg)
    assert kind == errors.KIND_SSL
    assert "离线完整版" in hint


def test_classify_http():
    kind, hint = errors.classify_error("HTTP 404：https://example.com/x.zip")
    assert kind == errors.KIND_HTTP
    assert "未公开" in hint
    kind2, _ = errors.classify_error("HTTP 403：forbidden")
    assert kind2 == errors.KIND_HTTP


def test_classify_timeout_and_network():
    assert errors.classify_error("网络请求超时")[0] == errors.KIND_NETWORK
    assert errors.classify_error("网络连接失败：timed out")[0] == errors.KIND_NETWORK


def test_classify_unknown():
    kind, hint = errors.classify_error("something weird")
    assert kind == errors.KIND_UNKNOWN
    assert "离线完整版" in hint
