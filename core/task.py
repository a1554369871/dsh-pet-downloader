# -*- coding: utf-8 -*-
"""后台安装任务：下载 → 安装 → 写数据根 → 可选 AI 配置 / 快捷方式 / 启动。"""
from __future__ import annotations

import os
from pathlib import Path
from threading import Event

from PySide6.QtCore import QThread, Signal

from . import api_config, installer, payload, releases, site_config
from . import source as source_mod
from .downloader import DownloadCancelled, download_file


class InstallTask(QThread):
    progress = Signal(int, int)
    status = Signal(str)
    log = Signal(str)
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, params: dict, parent=None) -> None:
        super().__init__(parent)
        self.params = dict(params)
        self.cancel_event = Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    # ------------------------------------------------------------------
    def run(self) -> None:
        try:
            result = self._run()
        except DownloadCancelled:
            self.failed.emit("已取消")
        except Exception as exc:  # noqa: BLE001 - 汇报给界面
            self.failed.emit(str(exc))
        else:
            self.done.emit(result)

    # ------------------------------------------------------------------
    def _run(self) -> dict:
        p = self.params
        variant_key = p["variant_key"]
        method = p["method"]
        install_dir = Path(p["install_dir"])
        variant = site_config.VARIANTS[variant_key]
        data_dir = install_dir / site_config.DATA_DIR_NAME

        bundled = payload.asset_path(variant_key) if method == "setup" else None
        if bundled is not None:
            # 离线自包含：直接使用内置安装包，不访问任何下载路径。
            self.log.emit(
                f"离线安装 · 内置 {variant['label']}（v{payload.bundled_version() or '?'}）"
            )
            self.log.emit(f"内置安装包：{bundled}")
            self.status.emit("正在离线安装（内置安装包）…")
            code, output = installer.run_setup_silent(
                bundled, install_dir, desktop_shortcut=bool(p.get("desktop_shortcut"))
            )
            if output.strip():
                self.log.emit(output.strip())
            if code != 0:
                raise RuntimeError(f"安装包返回错误码 {code}")
            exe = installer.exe_path(install_dir, variant_key)
            self.log.emit("安装包安装完成")
        else:
            source_cfg = p.get("source")
            if not isinstance(source_cfg, dict):
                source_cfg = source_mod.resolve()
            manifest = p.get("manifest") or releases.fetch_manifest(source=source_cfg)
            filename, url = releases.resolve(variant_key, method, manifest)
            self.log.emit(
                f"在线安装 · 版本 {manifest.get('version', '?')} · {variant['label']}"
            )
            self.log.emit(f"下载地址：{url}")

            target = installer.temp_download_dir() / filename
            self.status.emit(f"正在下载 {filename} …")
            download_file(
                url,
                target,
                progress=lambda done, total: self.progress.emit(done, total),
                cancel=self.cancel_event,
                timeout=60.0,
            )
            size_mb = target.stat().st_size / (1024 * 1024)
            self.log.emit(f"下载完成：{target.name}（{size_mb:.1f} MB）")

            if method == "setup":
                self.status.emit("正在静默安装（可能需要一两分钟）…")
                code, output = installer.run_setup_silent(
                    target, install_dir, desktop_shortcut=bool(p.get("desktop_shortcut"))
                )
                if output.strip():
                    self.log.emit(output.strip())
                if code != 0:
                    raise RuntimeError(f"安装包返回错误码 {code}")
                exe = installer.exe_path(install_dir, variant_key)
                self.log.emit("安装包安装完成")
            else:
                self.status.emit("正在解压…")
                installer.extract_zip(
                    target,
                    install_dir,
                    progress=lambda done, total: self.progress.emit(done, total),
                )
                exe = installer.exe_path(install_dir, variant_key)
                self.log.emit("解压完成")
                installer.write_uninstall_bat(install_dir, variant_key)

        # 数据根 marker + 全局指针（跟随安装盘符）
        installer.write_marker(install_dir, data_dir)
        installer.write_pointer(data_dir)
        self.log.emit(f"数据目录：{data_dir}")

        # 可选 AI 配置（仅 Chat 版）
        if variant["has_chat"] and p.get("ai_enabled"):
            api_key = str(p.get("api_key") or "").strip()
            config_file = api_config.write_ai_config(
                data_dir,
                variant["data_dir"],
                base_url=p.get("base_url") or site_config.DEFAULT_BASE_URL,
                model=p.get("model") or site_config.DEFAULT_MODEL,
                api_key=api_key,
                provider_name=p.get("provider_name") or "DeepSeek",
            )
            keyring_ok = api_config.store_keyring(api_key) if api_key else False
            self.log.emit(f"已写入 AI 配置：{config_file}")
            if api_key:
                self.log.emit(
                    "API Key 已写入系统钥匙串" if keyring_ok else "API Key 已写入配置文件（钥匙串不可用）"
                )

        # 绿色版可选创建桌面快捷方式（安装包由 /TASKS 处理）
        shortcut = None
        if method == "zip" and p.get("desktop_shortcut"):
            shortcut = self._desktop_lnk(install_dir, variant_key)
            if installer.create_shortcut(shortcut, exe, install_dir):
                self.log.emit(f"已创建桌面快捷方式：{shortcut.name}")
            else:
                self.log.emit("创建桌面快捷方式失败（可手动创建）")

        launched = False
        if p.get("launch") and exe.is_file():
            launched = installer.launch(exe, install_dir)
            self.log.emit("已启动 dsh-pet" if launched else "启动失败，请手动运行")

        return {
            "install_dir": str(install_dir),
            "data_dir": str(data_dir),
            "exe": str(exe),
            "shortcut": str(shortcut) if shortcut else "",
            "launched": launched,
        }

    # ------------------------------------------------------------------
    def _desktop_lnk(self, install_dir: Path, variant_key: str) -> Path:
        desktop = Path.home() / "Desktop"
        if not desktop.is_dir():
            base = os.environ.get("USERPROFILE") or str(Path.home())
            desktop = Path(base) / "Desktop"
        return desktop / f"dsh-pet {site_config.VARIANTS[variant_key]['data_dir']}.lnk"
