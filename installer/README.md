# Installer Generator

Standalone PyQt6 tool that generates professional Windows installers (`.exe`) from a YAML config file. Works alongside the ALM viewer — same dark theme, same `python -m <tool>` launch pattern.

## Launch

```bash
python -m installer
```

## Prerequisites

Install **one** installer compiler:

| Tool | Download | Default path |
|------|----------|--------------|
| **Inno Setup 6** (recommended) | https://jrsoftware.org/isinfo.php | `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` |
| **NSIS** | https://nsis.sourceforge.io/ | `C:\Program Files (x86)\NSIS\makensis.exe` |

Python dependencies:

```bash
pip install PyQt6 jinja2 pyyaml
pip install cryptography   # optional — only needed for RSA key generation / signing
```

## Workflow

1. **Package your app** first using PyInstaller or Nuitka → `dist/` folder
2. **Create a config** — copy `config_example.yaml` and edit it
3. **Open the GUI** → `python -m installer`
4. Open config → click **▶ Build Installer** (or press F5)
5. The finished `<AppName>_<Version>_Setup.exe` appears in `installer_output/`

## Features

| Feature | Notes |
|---------|-------|
| Install dir selection | User-configurable via wizard |
| Desktop + Start Menu shortcuts | Toggle per config |
| Uninstall | Registered in Add/Remove Programs with full rollback |
| License screen | Point `license:` at any `.txt` file |
| Version metadata | Embedded in the .exe via `VIProductVersion` |
| Silent install | Pass `/SILENT` or `/VERYSILENT` at the command line |
| Install log | Pass `/LOG=<path>` at runtime |
| Rollback on failure | Automatic (Inno Setup default behaviour) |
| Auto-update | SHA-256 verified; optional RSA-PSS signature; HTTPS-only |
| Code protection | Nuitka → native binary; UPX compression |

## Auto-Update

Copy `updater_stub.py` into your application source and call it at startup:

```python
# main.py
from updater_stub import check_for_updates
check_for_updates()   # silent; only acts when a newer version is found
```

The installer writes `updater_config.json` next to the executable at install time — no manual configuration needed at runtime.

Only `https://` URLs are accepted; `http://` and `file://` are rejected to prevent SSRF / downgrade attacks.

### GitHub Releases (recommended — free, no server needed)

set `update.enabled: true` and `update.github_repo: "owner/repo"` in config.  
Leave `check_url` empty. The updater calls:

```
GET https://api.github.com/repos/<owner>/<repo>/releases/latest
```

It compares `tag_name` (strip leading `v`) with the installed version, then downloads the first release asset whose filename contains `github_asset_pattern` (default `_Setup.exe`).

**Per-release checklist** (after `python -m installer` builds the `.exe`):

1. Create a GitHub Release with the version as the tag (e.g. `v1.1.0`).
2. Upload the installer:  `MyApp_1.1.0_Setup.exe`
3. Generate and upload the checksum file:
   ```bash
   python -c "from installer.signer import sha256_file; from pathlib import Path; h=sha256_file(Path('MyApp_1.1.0_Setup.exe')); Path('MyApp_1.1.0_Setup.exe.sha256').write_text(h+'  MyApp_1.1.0_Setup.exe')"
   ```
   Upload: `MyApp_1.1.0_Setup.exe.sha256`
4. *(Optional)* Upload a `.sig` file if RSA signing is enabled:
   ```python
   from installer.signer import sign_file
   from pathlib import Path
   sig = sign_file(Path("MyApp_1.1.0_Setup.exe"), Path("keys/private.pem"))
   Path("MyApp_1.1.0_Setup.exe.sig").write_bytes(sig)
   ```
   Upload: `MyApp_1.1.0_Setup.exe.sig`

That's it — no manifest file to maintain manually.

### Custom manifest (when GitHub is not used)

Set `update.check_url` to an `https://` URL serving this JSON:

```json
{
  "version": "1.1.0",
  "sha256": "<hex digest>",
  "download_url": "https://example.com/releases/MyApp_1.1.0_Setup.exe",
  "signature_url": "",
  "release_notes": "Bug fixes."
}
```

## Code Protection

| Config value | Protection level | Notes |
|---|---|---|
| `packer: "nuitka"` | High | Compiles Python → C → native binary; difficult to reverse |
| `packer: "pyinstaller"` | Low | Bundled bytecode; easy to unpack with standard tools |
| `packer: "none"` | None | You handle packaging separately |
| `upx: true` | Compression only | Reduces file size; minor obfuscation |

## RSA Signing (optional)

Use the GUI (**Auto-Update** tab → **Generate RSA-4096 Key Pair…**) or CLI:

```python
from installer.signer import generate_keypair, sign_file, sha256_file
from pathlib import Path

priv, pub = generate_keypair(Path("keys/"))
sig = sign_file(Path("installer_output/MyApp_1.1.0_Setup.exe"), priv)
Path("installer_output/MyApp_1.1.0_Setup.exe.sig").write_bytes(sig)
```

Bundle `public.pem` with your app as `update_public.pem`; keep `private.pem` secret.

## File Structure

```
installer/
├── __init__.py          ← version
├── __main__.py          ← entry: python -m installer
├── config.py            ← BuildConfig dataclasses + YAML loader
├── builder.py           ← Jinja2 rendering + ISCC/makensis subprocess
├── signer.py            ← SHA-256 + RSA-PSS key-gen / sign / verify
├── updater_stub.py      ← copy into your app; handles update checks at runtime
├── main_window.py       ← PyQt6 GUI
├── theme.py             ← dark QSS theme
├── config_example.yaml  ← annotated example config
└── templates/
    ├── setup.iss.j2     ← Inno Setup 6 script template
    └── setup.nsi.j2     ← NSIS script template
```
