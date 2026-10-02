# -*- coding: utf-8 -*-
"""盘符枚举与默认安装目录选择（Windows；其他平台给出合理回退）。"""
from __future__ import annotations

import os
import string
import sys
from pathlib import Path

DRIVE_FIXED = 3


def list_fixed_drives() -> list[str]:
    """返回本机固定磁盘盘符（形如 ``["C", "D", ...]``）。"""
    if sys.platform != "win32":
        home = Path.home()
        return [home.drive.rstrip(":") or "/"]
    try:
        import ctypes

        mask = ctypes.windll.kernel32.GetLogicalDrives()
        drives: list[str] = []
        for index, letter in enumerate(string.ascii_uppercase):
            if mask & (1 << index):
                root = f"{letter}:\\"
                if ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root)) == DRIVE_FIXED:
                    drives.append(letter)
        return drives
    except Exception:
        # 兜底：探测 A-Z 下是否存在（避免误列光驱/网络盘）
        drives = []
        for letter in string.ascii_uppercase:
            root = Path(f"{letter}:\\")
            if root.exists():
                drives.append(letter)
        return drives


def _drive_exists(letter: str) -> bool:
    return Path(f"{letter}:\\").exists()


def default_install_dir(variant_dir: str) -> Path:
    """默认安装目录：优先 D 盘（用户要求默认 D），其次首个非系统固定盘，最后用户目录。"""
    preferred = "D"
    if _drive_exists(preferred):
        return Path(f"{preferred}:\\") / "dsh-pet" / variant_dir
    for letter in list_fixed_drives():
        if letter.upper() != "C":
            return Path(f"{letter}:\\") / "dsh-pet" / variant_dir
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "Programs" / "dsh-pet" / variant_dir


def data_dir_for(install_dir: Path) -> Path:
    """安装目录对应的数据根（安装目录下的 data/）。"""
    return Path(install_dir) / "data"


def is_writable(path: Path) -> bool:
    """判断目录（或其最近存在的父目录）是否可写。"""
    probe = Path(path)
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        test = probe / ".dsh-pet-write-test.tmp"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return True
    except OSError:
        return False
