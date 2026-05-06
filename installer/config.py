"""Configuration — dataclasses and YAML loader for the installer tool."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AppConfig:
    name: str
    version: str
    publisher: str
    description: str
    exe_name: str
    icon: str = ""
    license_file: str = ""
    app_id: str = field(default_factory=lambda: str(uuid.uuid4()).upper())


@dataclass
class PathsConfig:
    source_dir: str = "dist/"
    output_dir: str = "installer_output/"
    default_install_dir: str = "{pf}\\MyApplication"


@dataclass
class ShortcutsConfig:
    desktop: bool = True
    start_menu: bool = True
    start_menu_folder: str = ""


@dataclass
class UpdateConfig:
    enabled: bool = False
    # GitHub Releases mode — set owner/repo (e.g. "acme/myapp") to use GitHub.
    # When set, check_url is ignored; the GitHub Releases API is used instead.
    github_repo: str = ""
    # Asset name pattern to match in the GitHub release (exact or substring)
    github_asset_pattern: str = "_Setup.exe"
    # Custom manifest mode — used only when github_repo is empty
    check_url: str = ""
    interval_hours: int = 24
    verify_checksum: bool = True
    verify_signature: bool = False
    public_key_file: str = ""


@dataclass
class ProtectionConfig:
    packer: str = "none"  # "nuitka" | "pyinstaller" | "none"
    upx: bool = False


@dataclass
class PackageConfig:
    """PyInstaller bundling settings."""
    enabled: bool = False
    # Path to the application entry-point script
    entry_script: str = ""                   # e.g. "run_gui.py"
    # Extra --paths arguments for PyInstaller
    extra_paths: str = ""                    # e.g. "src"
    # PyInstaller settings
    pyinstaller_onedir: bool = True          # --onedir (False = --onefile)
    pyinstaller_windowed: bool = True        # --windowed (no console)
    pyinstaller_extra_args: str = ""         # any extra CLI flags


@dataclass
class InstallerConfig:
    generator: str = "inno_setup"  # "inno_setup" | "nsis"
    inno_setup_path: str = r"C:\Users\Niket32\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
    nsis_path: str = r"C:\Program Files (x86)\NSIS\makensis.exe"
    silent_install_support: bool = True
    log_install: bool = True
    rollback_on_failure: bool = True


@dataclass
class BuildConfig:
    app: AppConfig
    paths: PathsConfig = field(default_factory=PathsConfig)
    shortcuts: ShortcutsConfig = field(default_factory=ShortcutsConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)
    protection: ProtectionConfig = field(default_factory=ProtectionConfig)
    package: PackageConfig = field(default_factory=PackageConfig)
    installer: InstallerConfig = field(default_factory=InstallerConfig)


def load_config(path: Path) -> BuildConfig:
    """Load and parse a config YAML file into a BuildConfig."""
    with path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    app_raw = raw.get("app", {})
    app = AppConfig(
        name=app_raw.get("name", "MyApp"),
        version=app_raw.get("version", "1.0.0"),
        publisher=app_raw.get("publisher", ""),
        description=app_raw.get("description", ""),
        exe_name=app_raw.get("exe_name", "app.exe"),
        icon=app_raw.get("icon", ""),
        license_file=app_raw.get("license", ""),
        app_id=app_raw.get("app_id", str(uuid.uuid4()).upper()),
    )

    # If app_id wasn't in the file, persist it now so every build uses the same GUID.
    # (Inno Setup uses AppId to key the uninstall entry in Add/Remove Programs.)
    if not app_raw.get("app_id"):
        _persist_app_id(path, app.app_id)

    paths_raw = raw.get("paths", {})
    paths = PathsConfig(
        source_dir=paths_raw.get("source_dir", "dist/"),
        output_dir=paths_raw.get("output_dir", "installer_output/"),
        default_install_dir=paths_raw.get("default_install_dir", "{pf}\\" + app.name),
    )

    sc_raw = raw.get("shortcuts", {})
    shortcuts = ShortcutsConfig(
        desktop=sc_raw.get("desktop", True),
        start_menu=sc_raw.get("start_menu", True),
        start_menu_folder=sc_raw.get("start_menu_folder", app.name),
    )

    upd_raw = raw.get("update", {})
    update = UpdateConfig(
        enabled=upd_raw.get("enabled", False),
        github_repo=upd_raw.get("github_repo", ""),
        github_asset_pattern=upd_raw.get("github_asset_pattern", "_Setup.exe"),
        check_url=upd_raw.get("check_url", ""),
        interval_hours=int(upd_raw.get("interval_hours", 24)),
        verify_checksum=upd_raw.get("verify_checksum", True),
        verify_signature=upd_raw.get("verify_signature", False),
        public_key_file=upd_raw.get("public_key_file", ""),
    )

    prot_raw = raw.get("protection", {})
    protection = ProtectionConfig(
        packer=prot_raw.get("packer", "none"),
        upx=prot_raw.get("upx", False),
    )

    pkg_raw = raw.get("package", {})
    package = PackageConfig(
        enabled=pkg_raw.get("enabled", False),
        entry_script=pkg_raw.get("entry_script", ""),
        extra_paths=pkg_raw.get("extra_paths", ""),
        pyinstaller_onedir=pkg_raw.get("pyinstaller_onedir", True),
        pyinstaller_windowed=pkg_raw.get("pyinstaller_windowed", True),
        pyinstaller_extra_args=pkg_raw.get("pyinstaller_extra_args", ""),
    )

    inst_raw = raw.get("installer", {})
    installer = InstallerConfig(
        generator=inst_raw.get("generator", "inno_setup"),
        inno_setup_path=inst_raw.get(
            "inno_setup_path", r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        ),
        nsis_path=inst_raw.get(
            "nsis_path", r"C:\Program Files (x86)\NSIS\makensis.exe"
        ),
        silent_install_support=inst_raw.get("silent_install_support", True),
        log_install=inst_raw.get("log_install", True),
        rollback_on_failure=inst_raw.get("rollback_on_failure", True),
    )

    return BuildConfig(
        app=app,
        paths=paths,
        shortcuts=shortcuts,
        update=update,
        protection=protection,
        package=package,
        installer=installer,
    )


def config_to_dict(c: BuildConfig) -> dict[str, Any]:
    """Serialize a BuildConfig back to a plain dict suitable for yaml.dump."""
    return {
        "app": {
            "name": c.app.name,
            "version": c.app.version,
            "publisher": c.app.publisher,
            "description": c.app.description,
            "exe_name": c.app.exe_name,
            "icon": c.app.icon,
            "license": c.app.license_file,
            "app_id": c.app.app_id,
        },
        "paths": {
            "source_dir": c.paths.source_dir,
            "output_dir": c.paths.output_dir,
            "default_install_dir": c.paths.default_install_dir,
        },
        "shortcuts": {
            "desktop": c.shortcuts.desktop,
            "start_menu": c.shortcuts.start_menu,
            "start_menu_folder": c.shortcuts.start_menu_folder,
        },
        "update": {
            "enabled": c.update.enabled,
            "github_repo": c.update.github_repo,
            "github_asset_pattern": c.update.github_asset_pattern,
            "check_url": c.update.check_url,
            "interval_hours": c.update.interval_hours,
            "verify_checksum": c.update.verify_checksum,
            "verify_signature": c.update.verify_signature,
        },
        "protection": {
            "packer": c.protection.packer,
            "upx": c.protection.upx,
        },
        "package": {
            "enabled": c.package.enabled,
            "entry_script": c.package.entry_script,
            "extra_paths": c.package.extra_paths,
            "pyinstaller_onedir": c.package.pyinstaller_onedir,
            "pyinstaller_windowed": c.package.pyinstaller_windowed,
            "pyinstaller_extra_args": c.package.pyinstaller_extra_args,
        },
        "installer": {
            "generator": c.installer.generator,
            "inno_setup_path": c.installer.inno_setup_path,
            "nsis_path": c.installer.nsis_path,
            "silent_install_support": c.installer.silent_install_support,
            "log_install": c.installer.log_install,
            "rollback_on_failure": c.installer.rollback_on_failure,
        },
    }


def _persist_app_id(config_path: Path, app_id: str) -> None:
    """Write app_id back into the YAML so it stays stable across builds."""
    try:
        text = config_path.read_text(encoding="utf-8")
        # Insert after the 'app:' block — find the exe_name line and add after it
        import re
        if re.search(r"^\s*app_id\s*:", text, re.MULTILINE):
            return  # already present, do nothing
        # Append app_id as a comment-preceded line after exe_name or version
        text = re.sub(
            r"(^\s*version\s*:.+)$",
            rf"\1\n  app_id: \"{app_id}\"",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        config_path.write_text(text, encoding="utf-8")
    except Exception:
        pass  # non-critical — failure just means a new UUID next time
