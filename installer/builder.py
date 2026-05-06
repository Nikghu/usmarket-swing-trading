"""Builder — renders installer scripts from Jinja2 templates and invokes the compiler."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

from jinja2 import Environment, FileSystemLoader

from installer.config import BuildConfig, PackageConfig
from installer.signer import sha256_file

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Jinja2 uses [[ ]] / [% %] to avoid clashing with Inno Setup's {…} and NSIS's ${…}
_JINJA_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    variable_start_string="[[",
    variable_end_string="]]",
    block_start_string="[%",
    block_end_string="%]",
    comment_start_string="[#",
    comment_end_string="#]",
    autoescape=False,
    keep_trailing_newline=True,
)

LogFn = Callable[[str], None]


class BuildError(RuntimeError):
    """Raised when any build step fails."""


# ── Public API ────────────────────────────────────────────────────────────────

def build(config: BuildConfig, log: LogFn = print, config_dir: Path | None = None) -> Path:
    """
    Full build pipeline:
      1. Render installer script from the appropriate Jinja2 template.
      2. Invoke ISCC.exe (Inno Setup) or makensis.exe (NSIS).
      3. Generate an update manifest with SHA-256 checksum.

    Returns the path to the generated installer .exe.
    """
    base = config_dir or Path.cwd()

    def _abs(p: str) -> str:
        """Resolve a path relative to the config file location."""
        if not p:
            return p
        resolved = (base / p).resolve()
        return str(resolved)

    # Resolve file-system paths that Inno Setup / NSIS must be able to open
    config = copy.deepcopy(config)
    config.app.icon = _abs(config.app.icon)
    config.app.license_file = _abs(config.app.license_file)
    config.paths.source_dir = _abs(config.paths.source_dir)
    config.paths.output_dir = _abs(config.paths.output_dir)

    # Validate that the packaged app directory exists before invoking the compiler
    src = Path(config.paths.source_dir)
    if not src.exists():
        raise BuildError(
            f"Source directory not found:\n  {src}\n"
            "Run the Package step (F4) first to build the application with PyInstaller."
        )

    output_dir = Path(config.paths.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if config.installer.generator == "inno_setup":
        installer_path = _build_inno(config, output_dir, log)
    elif config.installer.generator == "nsis":
        installer_path = _build_nsis(config, output_dir, log)
    else:
        raise BuildError(f"Unknown generator: {config.installer.generator!r}")

    if config.update.enabled:
        manifest_path = _write_manifest(installer_path, config, output_dir)
        log(f"Update manifest written → {manifest_path}")

    log(f"Build complete → {installer_path}")
    return installer_path


# ── Inno Setup ────────────────────────────────────────────────────────────────

def _build_inno(config: BuildConfig, output_dir: Path, log: LogFn) -> Path:
    iscc = Path(config.installer.inno_setup_path)
    if not iscc.exists():
        raise BuildError(
            f"Inno Setup compiler not found at:\n  {iscc}\n"
            "Install Inno Setup 6 from https://jrsoftware.org/isinfo.php"
        )

    script_path = output_dir / "setup.iss"
    icon_path = Path(config.app.icon) if config.app.icon else None
    icon_exists = bool(icon_path and icon_path.exists())
    extra = {
        "icon_name": icon_path.name if icon_exists else "",
        "icon_file": str(icon_path) if icon_exists else "",
    }
    _render("setup.iss.j2", config, script_path, extra=extra)
    log(f"Script rendered → {script_path}")

    result = subprocess.run(  # noqa: S603 — list form, no shell injection
        [str(iscc), str(script_path)],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        log(result.stdout.strip())
    if result.returncode != 0:
        raise BuildError(f"ISCC.exe exited {result.returncode}:\n{result.stderr}")

    # Remove intermediate script — it's only needed by ISCC during compilation
    try:
        script_path.unlink()
    except OSError:
        pass

    return output_dir / f"{config.app.name}_{config.app.version}_Setup.exe"


# ── NSIS ───────────────────────────────────────────────────────────────────────

def _build_nsis(config: BuildConfig, output_dir: Path, log: LogFn) -> Path:
    makensis = Path(config.installer.nsis_path)
    if not makensis.exists():
        raise BuildError(
            f"NSIS compiler not found at:\n  {makensis}\n"
            "Install NSIS from https://nsis.sourceforge.io/"
        )

    script_path = output_dir / "setup.nsi"
    _render("setup.nsi.j2", config, script_path)
    log(f"Script rendered → {script_path}")

    result = subprocess.run(  # noqa: S603
        [str(makensis), str(script_path)],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        log(result.stdout.strip())
    if result.returncode != 0:
        raise BuildError(f"makensis.exe exited {result.returncode}:\n{result.stderr}")

    return output_dir / f"{config.app.name}_{config.app.version}_Setup.exe"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _render(template_name: str, config: BuildConfig, dest: Path, extra: dict | None = None) -> None:
    tmpl = _JINJA_ENV.get_template(template_name)
    ctx: dict = {"c": config}
    if extra:
        ctx.update(extra)
    dest.write_text(tmpl.render(**ctx), encoding="utf-8")


def _write_manifest(installer_path: Path, config: BuildConfig, output_dir: Path) -> Path:
    checksum = sha256_file(installer_path) if installer_path.exists() else ""
    manifest = {
        "version": config.app.version,
        "description": config.app.description,
        "sha256": checksum,
        # Operator fills these after uploading the installer to the update server:
        "download_url": "",
        "signature_url": "",
        "release_notes": "",
    }
    manifest_path = output_dir / "updater_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


# ── Packaging pipeline: PyArmor → PyInstaller ────────────────────────────────

def package(
    cfg: PackageConfig,
    app_name: str,
    app_icon: str,
    log: LogFn = print,
    cwd: Path | None = None,
) -> Path:
    """
    Run PyInstaller to bundle the application.
    Returns the path to the dist/<app_name>/ output directory.
    """
    python = Path(sys.executable)
    run_dir = cwd or Path.cwd()
    dist_dir = _run_pyinstaller(cfg, python, app_name, app_icon, log, run_dir)
    log(f"\n✓ Package ready → {dist_dir}")
    return dist_dir


def _run_pyarmor(cfg: PackageConfig, python: Path, log: LogFn, cwd: Path) -> None:
    """Obfuscate cfg.pyarmor_src using PyArmor gen."""
    pyarmor_src = cfg.pyarmor_src
    if not pyarmor_src:
        raise BuildError("package.pyarmor_src must be set when pyarmor_enabled is true.")

    obf_out = Path(cfg.pyarmor_output)
    if not obf_out.is_absolute():
        obf_out = cwd / obf_out
    if obf_out.exists():
        log(f"Removing previous obfuscation output: {obf_out}")
        shutil.rmtree(obf_out)

    # PyArmor 9.x ships as a console script; use the sibling executable in the
    # same venv Scripts/ dir — "python -m pyarmor" is not supported.
    pyarmor_exe = python.parent / ("pyarmor.exe" if sys.platform == "win32" else "pyarmor")
    if not pyarmor_exe.exists():
        raise BuildError(
            f"pyarmor executable not found at {pyarmor_exe}. "
            "Run: pip install pyarmor"
        )

    cmd = [
        str(pyarmor_exe), "gen",
        "--output", str(obf_out),
    ]
    if cfg.pyarmor_recursive:
        cmd.append("--recursive")
    cmd.append(pyarmor_src)

    log(f"Running PyArmor: {' '.join(cmd)}\n")
    _stream_subprocess(cmd, log, cwd=cwd)


def _run_pyinstaller(
    cfg: PackageConfig,
    python: Path,
    app_name: str,
    app_icon: str,
    log: LogFn,
    cwd: Path,
) -> Path:
    """Bundle the app with PyInstaller, returning the dist output directory."""
    if not cfg.entry_script:
        raise BuildError("package.entry_script must point to your application's entry .py file.")

    cmd = [str(python), "-m", "PyInstaller", "--noconfirm"]

    if cfg.pyinstaller_onedir:
        cmd.append("--onedir")
    else:
        cmd.append("--onefile")

    if cfg.pyinstaller_windowed:
        cmd.append("--windowed")

    cmd += ["--name", app_name]

    if app_icon:
        icon_path = Path(app_icon)
        if not icon_path.is_absolute():
            icon_path = (cwd / app_icon).resolve()
        if icon_path.exists():
            cmd += ["--icon", str(icon_path)]

    if cfg.extra_paths:
        cmd += ["--paths", cfg.extra_paths]

    if cfg.pyinstaller_extra_args:
        cmd += cfg.pyinstaller_extra_args.split()

    cmd.append(cfg.entry_script)

    log(f"Running PyInstaller: {' '.join(cmd)}\n")
    _stream_subprocess(cmd, log, cwd=cwd)

    return cwd / "dist" / app_name


def _stream_subprocess(cmd: list[str], log: LogFn, cwd: Path | None = None) -> None:
    """Run a subprocess and stream its stdout+stderr line-by-line to log()."""
    proc = subprocess.Popen(  # noqa: S603 — cmd is always built from controlled inputs
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        log(line.rstrip())
    proc.wait()
    if proc.returncode != 0:
        raise BuildError(f"Process exited with code {proc.returncode}.")
