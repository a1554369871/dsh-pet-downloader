# -*- coding: utf-8 -*-
"""安装动作：解压绿色版 / 静默运行安装包 / 写数据根 marker / 快捷方式 / 启动。"""
from __future__ import annotations

import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

from . import site_config

USER_DATA_NAMES = (
    "config.json",
    "pet_journal.json",
    "pet_diary_chat.json",
    "sessions",
)


def temp_download_dir() -> Path:
    root = Path(tempfile.gettempdir()) / "dsh-pet-downloader"
    root.mkdir(parents=True, exist_ok=True)
    return root


def exe_path(install_dir: Path, variant_key: str) -> Path:
    return Path(install_dir) / site_config.VARIANTS[variant_key]["exe"]


def extract_zip(archive: Path, dest: Path, progress=None) -> Path:
    """把绿色版 zip 解压到 dest（zip 根即文件，平铺）。"""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        total = len(members) or 1
        for index, member in enumerate(members, start=1):
            zf.extract(member, dest)
            if progress is not None:
                progress(index, total)
    return dest


def run_setup_silent(setup: Path, dest: Path, *, desktop_shortcut: bool = False) -> tuple[int, str]:
    """静默运行 Inno Setup 安装包到指定目录，返回 (返回码, 输出)。"""
    args = [
        str(setup),
        "/SILENT",
        "/NORESTART",
        "/LANG=chinesesimp",
        f"/DIR={Path(dest)}",
    ]
    if desktop_shortcut:
        args.append("/TASKS=desktopicon")
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
    except subprocess.TimeoutExpired as exc:
        return 1, f"安装超时：{exc}"
    output = "\n".join(filter(None, [completed.stdout, completed.stderr]))
    return completed.returncode, output


def write_marker(install_dir: Path, data_dir: Path) -> Path:
    """在安装目录写数据根 marker（内容为绝对路径）。"""
    install_dir = Path(install_dir)
    install_dir.mkdir(parents=True, exist_ok=True)
    marker = install_dir / site_config.MARKER_NAME
    marker.write_text(str(Path(data_dir)), encoding="utf-8")
    return marker


def pointer_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return (
        Path(base)
        / site_config.POINTER_PARENT
        / site_config.POINTER_NAME
    )


def write_pointer(data_dir: Path) -> Path:
    """写全局数据根指针，供 DSH 桥接等外部工具定位。"""
    pointer = pointer_path()
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(str(Path(data_dir)), encoding="utf-8")
    return pointer


def create_shortcut(lnk: Path, target: Path, workdir: Path) -> bool:
    """用 WScript.Shell 创建 .lnk 快捷方式（Windows）。"""
    script = (
        "$ws = New-Object -ComObject WScript.Shell\n"
        f"$sc = $ws.CreateShortcut('{_ps(lnk)}')\n"
        f"$sc.TargetPath = '{_ps(target)}'\n"
        f"$sc.WorkingDirectory = '{_ps(workdir)}'\n"
        f"$sc.IconLocation = '{_ps(target)},0'\n"
        "$sc.Save()\n"
    )
    fd, path = tempfile.mkstemp(suffix=".ps1")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(script)
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        return completed.returncode == 0
    except Exception:
        return False
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def launch(exe: Path, workdir: Path) -> bool:
    try:
        subprocess.Popen([str(exe)], cwd=str(workdir))
        return True
    except OSError:
        return False


def write_uninstall_bat(install_dir: Path, variant_key: str) -> Path:
    """为绿色版生成卸载脚本：清数据 + 自删目录。"""
    install_dir = Path(install_dir)
    exe = site_config.VARIANTS[variant_key]["exe"]
    bat = install_dir / "Uninstall.bat"
    content = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "set \"DIR=%~dp0\"\r\n"
        "echo 正在卸载 dsh-pet 并清除全部用户数据...\r\n"
        f"if exist \"%DIR%{exe}\" \"%DIR%{exe}\" --uninstall-cleanup\r\n"
        "rmdir /s /q \"%DIR%data\" 2>nul\r\n"
        f"del /q \"%DIR%{site_config.MARKER_NAME}\" 2>nul\r\n"
        "del /q \"%APPDATA%\\dsh-pet\\data-root.txt\" 2>nul\r\n"
        "echo 完成，正在删除安装目录...\r\n"
        "start \"\" cmd /c ping -n 2 127.0.0.1 >nul & rmdir /s /q \"%DIR%\"\r\n"
    )
    bat.write_text(content, encoding="utf-8")
    return bat


def find_user_data(bundle_root: Path) -> list[str]:
    """扫描一个产物目录，返回疑似用户数据文件/目录（发布产物应为空）。"""
    found: list[str] = []
    bundle_root = Path(bundle_root)
    for name in USER_DATA_NAMES:
        for match in bundle_root.rglob(name):
            found.append(str(match.relative_to(bundle_root)))
    return found


def _ps(path: Path) -> str:
    """PowerShell 单引号字符串转义。"""
    return str(path).replace("'", "''")
