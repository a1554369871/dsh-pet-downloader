# -*- coding: utf-8 -*-
"""下载器主界面：分步向导（欢迎 → 版本 → 位置 → AI → 选项 → 安装 → 完成）。"""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core import ai_presets, api_config, drives, payload, releases, site_config
from core import source as source_mod
from core.task import InstallTask

P_WELCOME = 0
P_VARIANT = 1
P_LOCATION = 2
P_AI = 3
P_OPTIONS = 4
P_PROGRESS = 5
P_FINISH = 6

STEP_LABELS = ("欢迎", "版本与方式", "安装位置", "AI 配置", "安装", "完成")


class ManifestFetcher(QObject):
    """后台（守护线程）拉取版本清单，避免阻塞界面，且不影响进程退出。"""

    fetched = Signal(dict)

    def start(self) -> None:
        threading.Thread(target=self._work, daemon=True, name="manifest-fetch").start()

    def _work(self) -> None:
        try:
            self.fetched.emit(releases.fetch_manifest(timeout=6.0))
        except Exception:
            pass


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{site_config.APP_NAME} · dsh-pet")
        self.setMinimumSize(700, 580)
        self._task: InstallTask | None = None
        self._fetcher: ManifestFetcher | None = None
        self._manifest: dict = {}
        self._dir_touched = False
        self._install_failed = False
        self.offline_variants = payload.available_variants()
        self.bundled_version = payload.bundled_version()
        self._build()
        self._update_method_availability()
        self._update_ai_availability()
        self._go(P_WELCOME)
        self._fetch_manifest()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("wizardRoot")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 18, 22, 16)
        outer.setSpacing(12)

        title = QLabel("蓝色大肥鱼 · dsh-pet 下载器")
        title.setObjectName("appTitle")
        outer.addWidget(title)
        subtitle = QLabel("几步选好版本与安装位置，自动下载安装；AI 配置可选。")
        subtitle.setObjectName("appSubtitle")
        outer.addWidget(subtitle)
        self.version_label = QLabel()
        self.version_label.setObjectName("versionLabel")
        outer.addWidget(self.version_label)
        self._update_version_label()

        step_bar = QHBoxLayout()
        step_bar.setSpacing(8)
        self.step_labels: list[QLabel] = []
        for label in STEP_LABELS:
            chip = QLabel(label)
            chip.setObjectName("step")
            chip.setProperty("state", "normal")
            self.step_labels.append(chip)
            step_bar.addWidget(chip)
        step_bar.addStretch(1)
        outer.addLayout(step_bar)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)
        self._build_welcome()
        self._build_variant()
        self._build_location()
        self._build_ai()
        self._build_options()
        self._build_progress()
        self._build_finish()

        nav = QHBoxLayout()
        self.back_btn = QPushButton("上一步")
        self.back_btn.clicked.connect(self._on_back)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._cancel)
        self.primary_btn = QPushButton("下一步")
        self.primary_btn.setObjectName("primary")
        self.primary_btn.setMinimumHeight(38)
        self.primary_btn.clicked.connect(self._on_primary)
        nav.addWidget(self.back_btn)
        nav.addStretch(1)
        nav.addWidget(self.cancel_btn)
        nav.addWidget(self.primary_btn)
        outer.addLayout(nav)

    def _page(self, title: str, hint: str = "") -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(10)
        head = QLabel(title)
        head.setObjectName("pageTitle")
        layout.addWidget(head)
        if hint:
            note = QLabel(hint)
            note.setObjectName("pageHint")
            note.setWordWrap(True)
            layout.addWidget(note)
        return page, layout

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        return card, layout

    # -- pages ---------------------------------------------------------
    def _build_welcome(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch(1)
        hello = QLabel("欢迎使用蓝色大肥鱼 · dsh-pet 下载器")
        hello.setObjectName("welcomeTitle")
        hello.setWordWrap(True)
        hello.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hello)
        desc = QLabel(
            "接下来会用几步帮你选择版本与安装方式、安装盘符，并可选择填写 AI 配置。\n"
            "下载安装完成后，用户数据默认保存在所选安装目录的 data\\ 下。"
        )
        desc.setObjectName("pageHint")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        tip = QLabel("功能介绍与使用方法请查看官网（右上/完成页均有入口）。")
        tip.setObjectName("fieldHint")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip)
        layout.addStretch(2)
        self.stack.addWidget(page)

    def _option_row(self, title: str, desc: str, checked: bool) -> QRadioButton:
        radio = QRadioButton(title)
        radio.setChecked(checked)
        return radio

    def _build_variant(self) -> None:
        page, layout = self._page(
            "选择版本与安装方式",
            "不知道选哪个就用默认：Chat 版功能最全，绿色版解压即用、删除即卸载。",
        )
        card, card_layout = self._card()
        variant_label = QLabel("版本")
        variant_label.setStyleSheet("font-weight: 600; color: #0f172a;")
        card_layout.addWidget(variant_label)
        self.rb_chat = self._option_row(
            "Chat 版（含 AI 对话，推荐）", "", True
        )
        self.rb_plain = self._option_row("无 Chat 版（只有桌宠，更轻量）", "", False)
        group_variant = QButtonGroup(self)
        group_variant.addButton(self.rb_chat)
        group_variant.addButton(self.rb_plain)
        card_layout.addWidget(self.rb_chat)
        card_layout.addWidget(self.rb_plain)
        method_label = QLabel("安装方式")
        method_label.setStyleSheet("font-weight: 600; color: #0f172a; margin-top: 8px;")
        card_layout.addWidget(method_label)
        self.rb_zip = QRadioButton("绿色版（解压到所选目录，删除即卸载）")
        self.rb_setup = QRadioButton("安装包（静默安装，含卸载程序）")
        self.rb_zip.setChecked(True)
        group_method = QButtonGroup(self)
        group_method.addButton(self.rb_zip)
        group_method.addButton(self.rb_setup)
        card_layout.addWidget(self.rb_zip)
        card_layout.addWidget(self.rb_setup)
        self.method_note = QLabel()
        self.method_note.setObjectName("fieldHint")
        self.method_note.setWordWrap(True)
        card_layout.addWidget(self.method_note)
        source_label = QLabel("在线下载源（离线自包含版不使用）")
        source_label.setStyleSheet("font-weight: 600; color: #0f172a; margin-top: 8px;")
        card_layout.addWidget(source_label)
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("留空 = 官方 GitHub Releases；可填自建 manifest.json 地址")
        card_layout.addWidget(self.source_edit)
        layout.addWidget(card)
        layout.addStretch(1)
        self.rb_chat.toggled.connect(self._on_variant_changed)
        self.rb_plain.toggled.connect(self._on_variant_changed)
        self.stack.addWidget(page)

    def _update_method_availability(self) -> None:
        key = self._variant_key()
        offline = key in self.offline_variants
        if offline:
            self.rb_setup.setChecked(True)
            self.rb_zip.setEnabled(False)
            self.rb_setup.setEnabled(True)
            self.method_note.setText(
                f"检测到内置安装包（v{self.bundled_version or '?'}），将<b>离线安装</b>，无需联网。"
            )
            self.source_edit.setEnabled(False)
        else:
            self.rb_zip.setEnabled(True)
            self.rb_setup.setEnabled(True)
            self.method_note.setText("未检测到内置安装包，将从在线下载源下载安装。")
            self.source_edit.setEnabled(True)

    def _build_location(self) -> None:
        page, layout = self._page(
            "选择安装位置",
            "默认 D 盘（不存在时自动回退到其他盘）。不修改直接下一步即使用默认目录。",
        )
        card, card_layout = self._card()
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        self.dir_edit = QLineEdit()
        self.dir_edit.textEdited.connect(self._on_dir_edited)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        row_layout.addWidget(self.dir_edit)
        row_layout.addWidget(browse)
        card_layout.addWidget(QLabel("安装目录"))
        card_layout.addWidget(row)
        self.data_label = QLabel()
        self.data_label.setObjectName("fieldHint")
        self.data_label.setWordWrap(True)
        card_layout.addWidget(self.data_label)
        layout.addWidget(card)
        layout.addStretch(1)
        self.stack.addWidget(page)

    def _build_ai(self) -> None:
        page, layout = self._page(
            "AI 配置（可选）",
            "选择服务商会自动填入 API 地址与模型，字段仍可手改；不填 Key 也能安装，之后在桌宠「AI 设置」里再配。",
        )
        self.ai_group = QFrame()
        self.ai_group.setObjectName("card")
        card_layout = QVBoxLayout(self.ai_group)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(8)

        self.ai_enable = QCheckBox("安装时写入 AI 配置")
        self.ai_enable.setChecked(True)
        card_layout.addWidget(self.ai_enable)

        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("服务商"))
        self.provider_combo = QComboBox()
        for preset in ai_presets.PROVIDERS:
            label = preset.name + ("（默认）" if preset.key == ai_presets.DEFAULT_KEY else "")
            self.provider_combo.addItem(label, preset.key)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_row.addWidget(self.provider_combo, 1)
        card_layout.addLayout(provider_row)

        self.api_url = QLineEdit()
        self.api_model = QLineEdit()
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("粘贴 API Key（如 sk-…）")
        for label, widget in (
            ("API 地址", self.api_url),
            ("模型", self.api_model),
            ("API Key", self.api_key),
        ):
            row = QHBoxLayout()
            tag = QLabel(label)
            tag.setFixedWidth(64)
            row.addWidget(tag)
            row.addWidget(widget, 1)
            card_layout.addLayout(row)

        test_row = QHBoxLayout()
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self._test_connection)
        self.test_label = QLabel("")
        self.test_label.setObjectName("fieldHint")
        self.test_label.setWordWrap(True)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_label, 1)
        card_layout.addLayout(test_row)

        self.ai_plain_note = QLabel("无 Chat 版不含 AI 对话，本步可跳过。")
        self.ai_plain_note.setObjectName("fieldHint")
        self.ai_plain_note.setVisible(False)
        card_layout.addWidget(self.ai_plain_note)

        layout.addWidget(self.ai_group)
        layout.addStretch(1)
        self._select_default_provider()
        self.stack.addWidget(page)

    def _build_options(self) -> None:
        page, layout = self._page("安装选项", "确认无误后点击「开始安装」，随后会开始下载。")
        card, card_layout = self._card()
        self.desktop_shortcut = QCheckBox("创建桌面快捷方式")
        self.launch_after = QCheckBox("安装完成后立即运行")
        self.launch_after.setChecked(True)
        card_layout.addWidget(self.desktop_shortcut)
        card_layout.addWidget(self.launch_after)
        self.summary_label = QLabel()
        self.summary_label.setObjectName("fieldHint")
        self.summary_label.setWordWrap(True)
        card_layout.addWidget(self.summary_label)
        layout.addWidget(card)
        layout.addStretch(1)
        self.stack.addWidget(page)

    def _build_progress(self) -> None:
        page, layout = self._page("正在下载并安装…", "")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status_label = QLabel("准备中…")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.log_toggle = QPushButton("显示详情")
        self.log_toggle.setObjectName("link")
        self.log_toggle.clicked.connect(self._toggle_log)
        layout.addWidget(self.log_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(160)
        self.log_view.setVisible(False)
        layout.addWidget(self.log_view)
        layout.addStretch(1)
        self.stack.addWidget(page)

    def _build_finish(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(10)
        hello = QLabel("谢谢安装！")
        hello.setObjectName("welcomeTitle")
        layout.addWidget(hello)
        text = QLabel("大肥鱼已经装好啦。下面可以直接打开使用教程，或去下载页 / Releases 看看。")
        text.setObjectName("pageHint")
        text.setWordWrap(True)
        layout.addWidget(text)
        card, card_layout = self._card()
        self.finish_install_label = QLabel()
        self.finish_data_label = QLabel()
        self.finish_install_label.setWordWrap(True)
        self.finish_data_label.setWordWrap(True)
        card_layout.addWidget(self.finish_install_label)
        card_layout.addWidget(self.finish_data_label)
        layout.addWidget(card)
        links = QHBoxLayout()
        for label, url in (
            ("使用教程", site_config.WEBSITE_GUIDE),
            ("下载页", site_config.WEBSITE_DOWNLOAD),
            ("GitHub Releases", site_config.RELEASES_PAGE),
        ):
            links.addWidget(self._link_button(label, url))
        self.open_dir_btn = QPushButton("打开安装目录")
        self.open_dir_btn.clicked.connect(self._open_install_dir)
        links.addWidget(self.open_dir_btn)
        links.addStretch(1)
        layout.addLayout(links)
        layout.addStretch(1)
        self.stack.addWidget(page)

    def _link_button(self, text: str, url: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("link")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
        return button

    # -- state ---------------------------------------------------------
    def _variant_key(self) -> str:
        return "chat" if self.rb_chat.isChecked() else "plain"

    def _method(self) -> str:
        return "setup" if self.rb_setup.isChecked() else "zip"

    def _update_version_label(self) -> None:
        if self.offline_variants:
            version = self.bundled_version or self._manifest.get("version") or site_config.VERSION
            self.version_label.setText(f"离线自包含版 · 内置 v{version}")
            return
        version = self._manifest.get("version") or site_config.VERSION
        source = "（联网获取）" if self._manifest.get("source") == "remote" else "（内嵌）"
        self.version_label.setText(f"在线版 · 当前版本 v{version} {source}")

    def _select_default_provider(self) -> None:
        for index in range(self.provider_combo.count()):
            if self.provider_combo.itemData(index) == ai_presets.DEFAULT_KEY:
                self.provider_combo.setCurrentIndex(index)
                break
        self._on_provider_changed(self.provider_combo.currentIndex())

    def _on_provider_changed(self, _index: int) -> None:
        key = self.provider_combo.currentData()
        preset = ai_presets.get(str(key))
        if preset.key == "custom":
            self.api_url.clear()
            self.api_model.clear()
        else:
            self.api_url.setText(preset.base_url)
            self.api_model.setText(preset.model)

    def _update_data_label(self) -> None:
        path = self.dir_edit.text().strip()
        self.data_label.setText(
            f"数据目录：{Path(path) / site_config.DATA_DIR_NAME}" if path else "数据目录：—"
        )

    def _refresh_default_dir(self) -> None:
        if self._dir_touched:
            return
        variant = site_config.VARIANTS[self._variant_key()]
        self.dir_edit.setText(str(drives.default_install_dir(variant["data_dir"])))
        self._update_data_label()

    def _on_dir_edited(self, _text: str) -> None:
        self._dir_touched = True
        self._update_data_label()

    def _on_variant_changed(self, checked: bool) -> None:
        if not checked:
            return
        self._update_ai_availability()
        self._update_method_availability()
        self._refresh_default_dir()

    def _update_ai_availability(self) -> None:
        is_chat = self._variant_key() == "chat"
        self.ai_group.setEnabled(is_chat)
        self.ai_plain_note.setVisible(not is_chat)

    def _browse(self) -> None:
        current = self.dir_edit.text().strip() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "选择安装目录", current)
        if chosen:
            self._dir_touched = True
            self.dir_edit.setText(chosen)
            self._update_data_label()

    def _update_summary(self) -> None:
        variant = site_config.VARIANTS[self._variant_key()]
        method = "安装包（setup.exe）" if self._method() == "setup" else "绿色版（zip）"
        if self._variant_key() in self.offline_variants:
            method = f"离线安装（内置安装包 · v{self.bundled_version or '?'}）"
        self.summary_label.setText(
            f"版本：{variant['label']}\n"
            f"安装方式：{method}\n"
            f"安装目录：{self.dir_edit.text().strip()}\n"
            f"数据目录：{Path(self.dir_edit.text().strip()) / site_config.DATA_DIR_NAME}"
        )

    # -- navigation ----------------------------------------------------
    def _set_step(self, active: int) -> None:
        for index, chip in enumerate(self.step_labels):
            state = "done" if index < active else ("active" if index == active else "normal")
            chip.setProperty("state", state)
            chip.style().unpolish(chip)
            chip.style().polish(chip)

    def _step_for_page(self, page: int) -> int:
        return {P_WELCOME: 0, P_VARIANT: 1, P_LOCATION: 2, P_AI: 3, P_OPTIONS: 4, P_PROGRESS: 4, P_FINISH: 5}.get(page, 0)

    def _go(self, page: int) -> None:
        if page == P_LOCATION:
            self._refresh_default_dir()
        elif page == P_AI:
            self._update_ai_availability()
        elif page == P_OPTIONS:
            self._update_summary()
        self.stack.setCurrentIndex(page)
        self._set_step(self._step_for_page(page))
        self._update_nav()

    def _update_nav(self) -> None:
        page = self.stack.currentIndex()
        self.back_btn.setVisible(page in (P_VARIANT, P_LOCATION, P_AI, P_OPTIONS))
        self.cancel_btn.setVisible(page == P_PROGRESS)
        self.primary_btn.setVisible(page != P_PROGRESS)
        if page in (P_WELCOME, P_VARIANT, P_LOCATION, P_AI):
            self.primary_btn.setText("下一步")
        elif page == P_OPTIONS:
            self.primary_btn.setText("开始安装")
        elif page == P_FINISH:
            self.primary_btn.setText("完成")

    def _on_primary(self) -> None:
        page = self.stack.currentIndex()
        if page == P_WELCOME:
            self._go(P_VARIANT)
        elif page == P_VARIANT:
            self._go(P_LOCATION)
        elif page == P_LOCATION:
            self._ensure_dir()
            self._go(P_AI)
        elif page == P_AI:
            self._go(P_OPTIONS)
        elif page == P_OPTIONS:
            self._start_install()
        elif page == P_FINISH:
            self.close()

    def _on_back(self) -> None:
        page = self.stack.currentIndex()
        if page in (P_VARIANT, P_LOCATION, P_AI, P_OPTIONS):
            self._go(page - 1)

    def _ensure_dir(self) -> None:
        text = self.dir_edit.text().strip()
        if not text:
            variant = site_config.VARIANTS[self._variant_key()]
            text = str(drives.default_install_dir(variant["data_dir"]))
            self.dir_edit.setText(text)
        self._update_data_label()

    def _toggle_log(self) -> None:
        visible = not self.log_view.isVisible()
        self.log_view.setVisible(visible)
        self.log_toggle.setText("隐藏详情" if visible else "显示详情")

    # -- manifest ------------------------------------------------------
    def _fetch_manifest(self) -> None:
        self._fetcher = ManifestFetcher(self)
        self._fetcher.fetched.connect(self._on_manifest)
        self._fetcher.start()

    def _on_manifest(self, manifest: dict) -> None:
        self._manifest = manifest
        self._update_version_label()

    # -- ai test -------------------------------------------------------
    def _test_connection(self) -> None:
        self.test_btn.setEnabled(False)
        self.test_label.setText("测试中…")
        self.test_label.setStyleSheet("color: #64748b;")
        ok, message = api_config.test_connection(
            self.api_url.text().strip(),
            self.api_model.text().strip(),
            self.api_key.text().strip(),
        )
        self.test_label.setText(message)
        self.test_label.setStyleSheet("color: #16a34a;" if ok else "color: #dc2626;")
        self.test_btn.setEnabled(True)

    # -- install -------------------------------------------------------
    def _start_install(self) -> None:
        install_dir = self.dir_edit.text().strip()
        target = Path(install_dir)
        if not install_dir or not drives.is_writable(target):
            QMessageBox.warning(self, "提示", f"目录不可写：{target}\n请返回上一步换一个可写目录。")
            self._go(P_LOCATION)
            return

        provider_key = str(self.provider_combo.currentData())
        preset = ai_presets.get(provider_key)
        method = "setup" if self._variant_key() in self.offline_variants else self._method()
        source_override: dict = {}
        source_url = self.source_edit.text().strip()
        if source_url:
            source_override["manifest_url"] = source_url
        params = {
            "variant_key": self._variant_key(),
            "method": method,
            "install_dir": str(target),
            "desktop_shortcut": self.desktop_shortcut.isChecked(),
            "launch": self.launch_after.isChecked(),
            "ai_enabled": self.ai_enable.isChecked() and self._variant_key() == "chat",
            "provider_name": preset.name,
            "base_url": self.api_url.text().strip() or preset.base_url,
            "model": self.api_model.text().strip() or preset.model,
            "api_key": self.api_key.text().strip(),
            "manifest": self._manifest,
            "source": source_mod.resolve(source_override),
        }

        self.log_view.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label.setText("准备中…")
        self._install_failed = False
        self._go(P_PROGRESS)

        self._task = InstallTask(params, self)
        self._task.progress.connect(self._on_progress)
        self._task.status.connect(self._on_status)
        self._task.log.connect(self._append_log)
        self._task.done.connect(self._on_done)
        self._task.failed.connect(self._on_failed)
        self._task.finished.connect(self._on_task_finished)
        self._task.start()

    def _cancel(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self.status_label.setText("正在取消…")

    def _on_progress(self, done: int, total: int) -> None:
        if total > 0:
            self.progress.setRange(0, 100)
            self.progress.setValue(min(100, int(done * 100 / total)))
        else:
            self.progress.setRange(0, 0)

    def _on_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _append_log(self, text: str) -> None:
        self.log_view.appendPlainText(text)

    def _on_done(self, result: dict) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.status_label.setText("安装完成")
        self._append_log(f"安装目录：{result.get('install_dir')}")
        self._append_log(f"数据目录：{result.get('data_dir')}")
        self._finish_result = result
        self.finish_install_label.setText(f"安装目录：{result.get('install_dir')}")
        self.finish_data_label.setText(f"数据目录：{result.get('data_dir')}")
        self._go(P_FINISH)

    def _on_failed(self, message: str) -> None:
        self._install_failed = True
        self.progress.setRange(0, 100)
        self.status_label.setText(f"失败：{message}")
        self._append_log(f"[错误] {message}")
        QMessageBox.critical(self, "安装失败", message)

    def _on_task_finished(self) -> None:
        self._task = None
        if self._install_failed:
            self._install_failed = False
            self._go(P_OPTIONS)

    def _open_install_dir(self) -> None:
        install_dir = getattr(self, "_finish_result", {}).get("install_dir", "")
        if install_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(install_dir))
