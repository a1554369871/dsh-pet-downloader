# -*- coding: utf-8 -*-
"""AI 服务商预设：供下载器「AI 配置」下拉框快速填入。

字段仍然可在界面手改；dsh-pet 走 OpenAI Chat Completions 兼容接口，
因此以下均为兼容端点。key 为内部标识，name 为下拉显示名。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderPreset:
    key: str
    name: str
    base_url: str
    model: str


PROVIDERS: tuple[ProviderPreset, ...] = (
    ProviderPreset("deepseek", "DeepSeek", "https://api.deepseek.com", "deepseek-v4-flash"),
    ProviderPreset(
        "glm", "智谱 GLM", "https://open.bigmodel.cn/api/paas/v4", "glm-4.6"
    ),
    ProviderPreset(
        "kimi", "Moonshot Kimi", "https://api.moonshot.cn/v1", "kimi-k2-0905-preview"
    ),
    ProviderPreset(
        "dashscope",
        "阿里云百炼（通义）",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "qwen-plus",
    ),
    ProviderPreset(
        "siliconflow",
        "硅基流动 SiliconFlow",
        "https://api.siliconflow.cn/v1",
        "deepseek-ai/DeepSeek-V3",
    ),
    ProviderPreset("openai", "OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"),
    ProviderPreset("custom", "自定义（手动填写）", "", ""),
)

DEFAULT_KEY = "deepseek"


def get(key: str) -> ProviderPreset:
    for preset in PROVIDERS:
        if preset.key == key:
            return preset
    return PROVIDERS[0]


def default() -> ProviderPreset:
    return get(DEFAULT_KEY)
