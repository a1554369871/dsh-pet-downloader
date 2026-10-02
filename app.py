# -*- coding: utf-8 -*-
"""dsh-pet 下载器入口。

运行：``python app.py``（开发）或双击打包后的 ``dsh-pet-downloader.exe``。
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    # 让 core/ui 在源码与打包两种方式下都可导入。
    base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)

    from PySide6.QtWidgets import QApplication

    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("dsh-pet-downloader")
    _apply_style(app)
    window = MainWindow()
    window.show()
    return app.exec()


def _apply_style(app) -> None:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "ui", "style.qss")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            app.setStyleSheet(handle.read())
    except OSError:
        pass


if __name__ == "__main__":
    sys.exit(main())
