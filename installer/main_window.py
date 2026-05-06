"""PyQt6 main window for the Installer Generator tool."""
from __future__ import annotations

import traceback
from pathlib import Path

import yaml
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from installer.builder import BuildError, build, package
from installer.config import BuildConfig, PackageConfig, config_to_dict, load_config
from installer.theme import apply_dark_theme


# ── Background worker — installer build ──────────────────────────────────────

class _BuildWorker(QObject):
    log_line = pyqtSignal(str)
    finished = pyqtSignal(str)   # installer path on success
    error = pyqtSignal(str)

    def __init__(self, config: BuildConfig, config_dir: Path) -> None:
        super().__init__()
        self._config = config
        self._config_dir = config_dir

    def run(self) -> None:
        try:
            path = build(self._config, log=self.log_line.emit, config_dir=self._config_dir)
            self.finished.emit(str(path))
        except BuildError as exc:
            self.error.emit(str(exc))
        except Exception:
            self.error.emit(traceback.format_exc())


# ── Background worker — packaging (PyArmor + PyInstaller) ────────────────────

class _PackageWorker(QObject):
    log_line = pyqtSignal(str)
    finished = pyqtSignal(str)   # dist dir on success
    error = pyqtSignal(str)

    def __init__(self, pkg_cfg: PackageConfig, app_name: str, app_icon: str, cwd: Path) -> None:
        super().__init__()
        self._pkg = pkg_cfg
        self._app_name = app_name
        self._app_icon = app_icon
        self._cwd = cwd

    def run(self) -> None:
        try:
            dist = package(self._pkg, self._app_name, self._app_icon, log=self.log_line.emit, cwd=self._cwd)
            self.finished.emit(str(dist))
        except BuildError as exc:
            self.error.emit(str(exc))
        except Exception:
            self.error.emit(traceback.format_exc())


# ── Main window ───────────────────────────────────────────────────────────────

class InstallerMainWindow(QMainWindow):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.setWindowTitle("Installer Generator")
        self.resize(1280, 760)
        self._config: BuildConfig | None = None
        self._config_path: Path | None = None
        self._thread: QThread | None = None
        self._pkg_thread: QThread | None = None

        apply_dark_theme(app)
        self._build_ui()
        self._connect_shortcuts()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)

        # Toolbar
        toolbar = QHBoxLayout()
        self._btn_open = QPushButton("Open config…  [Ctrl+O]")
        self._btn_save = QPushButton("Save config  [Ctrl+S]")
        self._btn_package = QPushButton("⚙  PyInstaller  [F4]")
        self._btn_package.setEnabled(False)
        self._btn_build = QPushButton("▶  Build Installer  [F5]")
        self._btn_build.setEnabled(False)
        for btn in (self._btn_open, self._btn_save, self._btn_package, self._btn_build):
            toolbar.addWidget(btn)
        toolbar.addStretch()
        root.addLayout(toolbar)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._tab_application(), "Application")
        tabs.addTab(self._tab_package(), "Package")
        tabs.addTab(self._tab_installer(), "Installer")
        tabs.addTab(self._tab_update(), "Auto-Update")

        # Log panel (right side)
        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(4, 0, 0, 0)
        log_hdr = QHBoxLayout()
        log_hdr.addWidget(QLabel("Build Log"))
        btn_clear = QPushButton("Clear")
        btn_clear.setFixedWidth(54)
        btn_clear.clicked.connect(lambda: self._log.clear())
        log_hdr.addStretch()
        log_hdr.addWidget(btn_clear)
        log_layout.addLayout(log_hdr)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 9))
        self._log.setStyleSheet("background:#1e1e1e; color:#e0e0e0;")
        log_layout.addWidget(self._log)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(tabs)
        splitter.addWidget(log_panel)
        splitter.setSizes([720, 560])
        root.addWidget(splitter)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

        self._btn_open.clicked.connect(self._open_config)
        self._btn_save.clicked.connect(self._save_config)
        self._btn_package.clicked.connect(self._start_package)
        self._btn_build.clicked.connect(self._start_build)

    def _tab_package(self) -> QWidget:
        """PyInstaller bundling settings."""
        w = QWidget()
        form = QFormLayout(w)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self._f_pkg_enabled = QCheckBox("Enable packaging step (PyInstaller)")
        form.addRow(self._f_pkg_enabled)

        # Entry point
        entry_row = QHBoxLayout()
        self._f_pkg_entry = QLineEdit()
        self._f_pkg_entry.setPlaceholderText("run_gui.py")
        btn_entry = QPushButton("Browse…")
        btn_entry.clicked.connect(self._browse_entry_script)
        entry_row.addWidget(self._f_pkg_entry)
        entry_row.addWidget(btn_entry)
        form.addRow("Entry script (.py):", entry_row)

        # PyInstaller section
        pyinst_lbl = QLabel("<b>PyInstaller bundling</b>")
        pyinst_lbl.setTextFormat(Qt.TextFormat.RichText)
        form.addRow(pyinst_lbl)

        self._f_pyinst_onedir = QCheckBox("--onedir  (folder output, recommended)")
        self._f_pyinst_onedir.setChecked(True)
        form.addRow(self._f_pyinst_onedir)

        self._f_pyinst_windowed = QCheckBox("--windowed  (no console window)")
        self._f_pyinst_windowed.setChecked(True)
        form.addRow(self._f_pyinst_windowed)

        self._f_pkg_extra_paths = QLineEdit()
        self._f_pkg_extra_paths.setPlaceholderText("src")
        form.addRow("Extra --paths (PyInstaller):", self._f_pkg_extra_paths)

        self._f_pyinst_extra = QLineEdit()
        self._f_pyinst_extra.setPlaceholderText("--collect-all PyQt6  (space-separated)")
        form.addRow("Extra PyInstaller flags:", self._f_pyinst_extra)

        note = QLabel(
            "<i>Tip: after packaging completes, source_dir is auto-filled from dist/&lt;AppName&gt;/.</i>"
        )
        note.setTextFormat(Qt.TextFormat.RichText)
        note.setWordWrap(True)
        form.addRow(note)
        return w

    def _browse_entry_script(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Select entry script", "", "Python files (*.py)")
        if p:
            self._f_pkg_entry.setText(p)
        if p:
            self._f_pkg_entry.setText(p)

    def _tab_application(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self._f_name = QLineEdit(); form.addRow("App name:", self._f_name)
        self._f_version = QLineEdit(); form.addRow("Version:", self._f_version)
        self._f_publisher = QLineEdit(); form.addRow("Publisher:", self._f_publisher)
        self._f_exe = QLineEdit(); form.addRow("Executable file:", self._f_exe)
        self._f_icon = QLineEdit(); form.addRow("Icon (.ico path):", self._f_icon)
        self._f_license = QLineEdit(); form.addRow("License file:", self._f_license)
        self._f_src = QLineEdit(); form.addRow("Source dir (dist/):", self._f_src)
        self._f_out = QLineEdit(); form.addRow("Output dir:", self._f_out)
        self._f_install_dir = QLineEdit()
        self._f_install_dir.setPlaceholderText("{pf}\\MyApplication")
        form.addRow("Default install dir:", self._f_install_dir)
        self._f_desktop = QCheckBox("Create desktop shortcut"); form.addRow(self._f_desktop)
        self._f_startmenu = QCheckBox("Create Start Menu shortcut"); form.addRow(self._f_startmenu)
        self._f_startmenu_folder = QLineEdit(); form.addRow("Start Menu folder:", self._f_startmenu_folder)
        return w

    def _tab_installer(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._f_generator = QComboBox()
        self._f_generator.addItems(["inno_setup", "nsis"])
        form.addRow("Generator:", self._f_generator)

        self._f_compiler = QLineEdit()
        form.addRow("Compiler path:", self._f_compiler)

        self._f_silent = QCheckBox("Silent install support (/SILENT flag)"); form.addRow(self._f_silent)
        self._f_log_install = QCheckBox("Write install log"); form.addRow(self._f_log_install)
        self._f_rollback = QCheckBox("Rollback on failure"); form.addRow(self._f_rollback)

        self._f_generator.currentTextChanged.connect(self._on_generator_changed)
        return w

    def _tab_update(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._f_upd_enabled = QCheckBox("Enable auto-update")
        form.addRow(self._f_upd_enabled)

        # ── GitHub Releases mode ──────────────────────────────────────────────
        gh_label = QLabel("<b>GitHub Releases (recommended)</b>")
        gh_label.setTextFormat(Qt.TextFormat.RichText)
        form.addRow(gh_label)

        self._f_gh_repo = QLineEdit()
        self._f_gh_repo.setPlaceholderText("owner/repo  e.g. acme/myapp")
        form.addRow("GitHub repo:", self._f_gh_repo)

        self._f_gh_asset = QLineEdit()
        self._f_gh_asset.setPlaceholderText("_Setup.exe")
        self._f_gh_asset.setText("_Setup.exe")
        form.addRow("Asset filename contains:", self._f_gh_asset)

        # ── Custom manifest mode ──────────────────────────────────────────────
        custom_label = QLabel("<b>Custom manifest (when GitHub repo is empty)</b>")
        custom_label.setTextFormat(Qt.TextFormat.RichText)
        form.addRow(custom_label)

        self._f_upd_url = QLineEdit()
        self._f_upd_url.setPlaceholderText("https://example.com/updates/manifest.json")
        form.addRow("Manifest URL (https only):", self._f_upd_url)

        # ── Common ────────────────────────────────────────────────────────────
        self._f_upd_hours = QSpinBox()
        self._f_upd_hours.setRange(1, 720)
        self._f_upd_hours.setValue(24)
        self._f_upd_hours.setSuffix(" hours")
        form.addRow("Check interval:", self._f_upd_hours)

        self._f_upd_checksum = QCheckBox("Verify SHA-256 checksum (recommended)")
        form.addRow(self._f_upd_checksum)

        self._f_upd_sig = QCheckBox("Verify RSA-PSS signature")
        form.addRow(self._f_upd_sig)

        btn_keygen = QPushButton("Generate RSA-4096 Key Pair…")
        btn_keygen.clicked.connect(self._generate_keys)
        form.addRow(btn_keygen)
        return w

    def _connect_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._open_config)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save_config)
        QShortcut(QKeySequence("F4"), self).activated.connect(self._start_package)
        QShortcut(QKeySequence("F5"), self).activated.connect(self._start_build)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_config(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open config", "", "YAML files (*.yaml *.yml);;All files (*)"
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            self._config = load_config(path)
            self._config_path = path
            self._populate_form()
            self._btn_build.setEnabled(True)
            self._btn_package.setEnabled(True)
            self.statusBar().showMessage(f"Loaded: {path}", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "Load Error", str(exc))

    def _save_config(self) -> None:
        if self._config_path is None:
            path_str, _ = QFileDialog.getSaveFileName(
                self, "Save config", "config.yaml", "YAML files (*.yaml)"
            )
            if not path_str:
                return
            self._config_path = Path(path_str)
        self._sync_form_to_config()
        if self._config is None:
            return
        with self._config_path.open("w", encoding="utf-8") as fh:
            yaml.dump(config_to_dict(self._config), fh, default_flow_style=False, allow_unicode=True)
        self.statusBar().showMessage(f"Saved: {self._config_path}", 4000)

    def _log_line(self, text: str) -> None:
        import html as _html
        lo = text.lower()
        if any(k in lo for k in ('✓', '→', 'complete', 'ready', ' ok', 'success', 'succeeded', 'finished')):
            color = '#4caf50'  # green
        elif any(k in text for k in ('✗', 'Error', 'error', 'Failed', 'failed', 'Traceback', 'exited with', 'Exception')):
            color = '#ef5350'  # red
        elif any(k in text for k in ('Warning', 'warning', 'WARN', 'warn')):
            color = '#ff9800'  # orange
        elif 'INFO' in text:
            color = '#9e9e9e'  # gray
        else:
            color = '#e0e0e0'  # default
        escaped = _html.escape(text).replace('\n', '<br>')
        self._log.append(f'<span style="color:{color};white-space:pre;">{escaped}</span>')

    def _start_build(self) -> None:
        if self._thread and self._thread.isRunning():
            return
        self._sync_form_to_config()
        if self._config is None:
            QMessageBox.warning(self, "No config", "Open or create a config file first.")
            return
        self._log.clear()
        self._log_line("Starting build…\n")
        self._btn_build.setEnabled(False)

        self._thread = QThread()
        self._worker = _BuildWorker(
            self._config,
            config_dir=self._config_path.parent if self._config_path else Path.cwd(),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.log_line.connect(self._log_line)
        self._worker.finished.connect(self._on_build_done)
        self._worker.error.connect(self._on_build_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_build_done(self, path: str) -> None:
        self._log_line(f"\n✓ Installer created: {path}")
        self.statusBar().showMessage("Build succeeded", 6000)
        self._btn_build.setEnabled(True)

    def _on_build_error(self, msg: str) -> None:
        self._log_line(f"\n✗ Build failed:\n{msg}")
        self.statusBar().showMessage("Build failed", 6000)
        self._btn_build.setEnabled(True)
    def _start_package(self) -> None:
        if self._pkg_thread and self._pkg_thread.isRunning():
            return
        self._sync_form_to_config()
        if self._config is None:
            QMessageBox.warning(self, "No config", "Open or create a config file first.")
            return
        pkg = self._config.package
        if not pkg.enabled:
            QMessageBox.information(
                self,
                "Packaging disabled",
                "Enable the packaging step in the Package tab first.",
            )
            return
        self._log.clear()
        self._log_line("Starting PyInstaller…\n")
        self._btn_package.setEnabled(False)

        self._pkg_thread = QThread()
        self._pkg_worker = _PackageWorker(
            pkg, self._config.app.name, self._config.app.icon,
            cwd=self._config_path.parent if self._config_path else Path.cwd(),
        )
        self._pkg_worker.moveToThread(self._pkg_thread)
        self._pkg_thread.started.connect(self._pkg_worker.run)
        self._pkg_worker.log_line.connect(self._log_line)
        self._pkg_worker.finished.connect(self._on_package_done)
        self._pkg_worker.error.connect(self._on_package_error)
        self._pkg_worker.finished.connect(self._pkg_thread.quit)
        self._pkg_worker.error.connect(self._pkg_thread.quit)
        self._pkg_thread.start()

    def _on_package_done(self, dist_dir: str) -> None:
        self._log_line(f"\n\u2713 Package ready: {dist_dir}")
        self._log_line(f"\u2192 Now set Application \u2192 Source dir to: {dist_dir}/")
        self.statusBar().showMessage("Packaging succeeded", 6000)
        self._btn_package.setEnabled(True)
        # Auto-fill source_dir to the dist output
        self._f_src.setText(dist_dir + "/")

    def _on_package_error(self, msg: str) -> None:
        self._log_line(f"\n\u2717 Packaging failed:\n{msg}")
        self.statusBar().showMessage("Packaging failed", 6000)
        self._btn_package.setEnabled(True)
    def _generate_keys(self) -> None:
        from installer.signer import generate_keypair

        out_dir_str = QFileDialog.getExistingDirectory(self, "Select output directory for key files")
        if not out_dir_str:
            return
        try:
            priv, pub = generate_keypair(Path(out_dir_str))
            QMessageBox.information(
                self,
                "Keys Generated",
                f"Private key: {priv}\nPublic key:  {pub}\n\n"
                "IMPORTANT:\n"
                "• Keep private.pem secret — never distribute it.\n"
                "• Bundle public.pem with your application as 'update_public.pem'.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Key Generation Failed", str(exc))

    def _on_generator_changed(self, text: str) -> None:
        current = self._f_compiler.text()
        if text == "inno_setup" and ("makensis" in current or not current):
            self._f_compiler.setText(r"C:\Users\Niket32\AppData\Local\Programs\Inno Setup 6\ISCC.exe")
        elif text == "nsis" and ("ISCC" in current or not current):
            self._f_compiler.setText(r"C:\Program Files (x86)\NSIS\makensis.exe")

    # ── Form ↔ Config sync ────────────────────────────────────────────────────

    def _populate_form(self) -> None:
        if self._config is None:
            return
        c = self._config
        self._f_name.setText(c.app.name)
        self._f_version.setText(c.app.version)
        self._f_publisher.setText(c.app.publisher)
        self._f_exe.setText(c.app.exe_name)
        self._f_icon.setText(c.app.icon)
        self._f_license.setText(c.app.license_file)
        self._f_src.setText(c.paths.source_dir)
        self._f_out.setText(c.paths.output_dir)
        self._f_install_dir.setText(c.paths.default_install_dir)
        self._f_desktop.setChecked(c.shortcuts.desktop)
        self._f_startmenu.setChecked(c.shortcuts.start_menu)
        self._f_startmenu_folder.setText(c.shortcuts.start_menu_folder)
        idx = self._f_generator.findText(c.installer.generator)
        if idx >= 0:
            self._f_generator.setCurrentIndex(idx)
        compiler = (
            c.installer.inno_setup_path
            if c.installer.generator == "inno_setup"
            else c.installer.nsis_path
        )
        self._f_compiler.setText(compiler)
        self._f_silent.setChecked(c.installer.silent_install_support)
        self._f_log_install.setChecked(c.installer.log_install)
        self._f_rollback.setChecked(c.installer.rollback_on_failure)
        self._f_upd_enabled.setChecked(c.update.enabled)
        self._f_gh_repo.setText(c.update.github_repo)
        self._f_gh_asset.setText(c.update.github_asset_pattern or "_Setup.exe")
        self._f_upd_url.setText(c.update.check_url)
        self._f_upd_hours.setValue(c.update.interval_hours)
        self._f_upd_checksum.setChecked(c.update.verify_checksum)
        self._f_upd_sig.setChecked(c.update.verify_signature)
        # Package tab
        self._f_pkg_enabled.setChecked(c.package.enabled)
        self._f_pkg_entry.setText(c.package.entry_script)
        self._f_pyinst_onedir.setChecked(c.package.pyinstaller_onedir)
        self._f_pyinst_windowed.setChecked(c.package.pyinstaller_windowed)
        self._f_pkg_extra_paths.setText(c.package.extra_paths)
        self._f_pyinst_extra.setText(c.package.pyinstaller_extra_args)

    def _sync_form_to_config(self) -> None:
        from installer.config import (
            AppConfig,
            BuildConfig,
            InstallerConfig,
            PackageConfig,
            PathsConfig,
            ProtectionConfig,
            ShortcutsConfig,
            UpdateConfig,
        )

        gen = self._f_generator.currentText()
        compiler = self._f_compiler.text()
        # Preserve app_id from the existing config so it doesn't change on each save
        existing_app_id = self._config.app.app_id if self._config else ""

        self._config = BuildConfig(
            app=AppConfig(
                name=self._f_name.text(),
                version=self._f_version.text(),
                publisher=self._f_publisher.text(),
                description="",
                exe_name=self._f_exe.text(),
                icon=self._f_icon.text(),
                license_file=self._f_license.text(),
                app_id=existing_app_id or "",
            ),
            paths=PathsConfig(
                source_dir=self._f_src.text(),
                output_dir=self._f_out.text(),
                default_install_dir=self._f_install_dir.text(),
            ),
            shortcuts=ShortcutsConfig(
                desktop=self._f_desktop.isChecked(),
                start_menu=self._f_startmenu.isChecked(),
                start_menu_folder=self._f_startmenu_folder.text(),
            ),
            update=UpdateConfig(
                enabled=self._f_upd_enabled.isChecked(),
                github_repo=self._f_gh_repo.text().strip(),
                github_asset_pattern=self._f_gh_asset.text().strip() or "_Setup.exe",
                check_url=self._f_upd_url.text(),
                interval_hours=self._f_upd_hours.value(),
                verify_checksum=self._f_upd_checksum.isChecked(),
                verify_signature=self._f_upd_sig.isChecked(),
            ),
            protection=ProtectionConfig(),
            package=PackageConfig(
                enabled=self._f_pkg_enabled.isChecked(),
                entry_script=self._f_pkg_entry.text(),
                extra_paths=self._f_pkg_extra_paths.text(),
                pyinstaller_onedir=self._f_pyinst_onedir.isChecked(),
                pyinstaller_windowed=self._f_pyinst_windowed.isChecked(),
                pyinstaller_extra_args=self._f_pyinst_extra.text(),
            ),
            installer=InstallerConfig(
                generator=gen,
                inno_setup_path=compiler if gen == "inno_setup" else r"C:\Users\Niket32\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
                nsis_path=compiler if gen == "nsis" else r"C:\Program Files (x86)\NSIS\makensis.exe",
                silent_install_support=self._f_silent.isChecked(),
                log_install=self._f_log_install.isChecked(),
                rollback_on_failure=self._f_rollback.isChecked(),
            ),
        )
