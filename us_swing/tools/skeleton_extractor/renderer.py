"""Phase 3 — MODULE_MAP.json generator (one file per source subfolder)."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from skeleton_extractor.extractor import FileSkeleton

_SRC_ROOT = Path(__file__).parents[2] / "src" / "us_swing"


def render_all(skeletons: dict[str, FileSkeleton]) -> None:
    grouped: dict[Path, list[FileSkeleton]] = defaultdict(list)
    for skel in skeletons.values():
        skel_path = Path(skel.path)
        try:
            rel = skel_path.relative_to(_SRC_ROOT)
        except ValueError:
            continue
        if len(rel.parts) < 2:
            continue
        subfolder = _SRC_ROOT / rel.parts[0]
        if not subfolder.is_dir():
            continue
        grouped[subfolder].append(skel)

    for subfolder, file_skels in sorted(grouped.items()):
        _render_subfolder(subfolder, sorted(file_skels, key=lambda s: s.path))


def _render_subfolder(subfolder: Path, file_skels: list[FileSkeleton]) -> None:
    tool_code = next((s.tool_code for s in file_skels if s.tool_code), None)
    payload: dict = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "subfolder": subfolder.name,
        "root": str(subfolder),
        "tool_code": tool_code,
        "files": {
            Path(s.path).name: _slim(s)
            for s in file_skels
        },
    }
    out_path = subfolder / "MODULE_MAP.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"  Written {out_path}")


def _slim(skel: FileSkeleton) -> dict:  # type: ignore[type-arg]
    """Return a MODULE_MAP-safe dict — orientation fields only.

    Stripped: path, file_hash, tool_code (hoisted to root), imports, calls (impact-analysis-only).
    Empty arrays and null values are omitted to reduce noise.
    Full data stays in skeleton.json for --usages queries.
    """
    from dataclasses import asdict
    d = asdict(skel)
    for key in ("path", "file_hash", "tool_code", "imports"):
        d.pop(key, None)
    for f in d.get("top_level_functions", []):
        f.pop("calls", None)
        f.pop("is_private", None)
    for cls in d.get("classes", []):
        for m in cls.get("methods", []):
            m.pop("calls", None)
            m.pop("is_private", None)
    return _drop_empty(d)


def _drop_empty(obj: object) -> object:
    """Recursively remove None values and empty lists/dicts."""
    if isinstance(obj, dict):
        return {k: _drop_empty(v) for k, v in obj.items() if v is not None and v != [] and v != {}}
    if isinstance(obj, list):
        return [_drop_empty(i) for i in obj]
    return obj


def token_stats(skeletons: dict[str, FileSkeleton]) -> None:
    print(f"\n{'File':<40} {'Raw tokens':>12} {'Skel tokens':>12} {'Savings':>8}")
    print("-" * 76)
    total_raw = total_skel = 0
    for skel in sorted(skeletons.values(), key=lambda s: s.path):
        raw_tok = len(Path(skel.path).read_bytes()) // 4
        skel_tok = _estimate_skeleton_tokens(skel)
        saving = (1 - skel_tok / max(raw_tok, 1)) * 100
        name = Path(skel.path).name
        print(f"{name:<40} {raw_tok:>12,} {skel_tok:>12,} {saving:>7.1f}%")
        total_raw += raw_tok
        total_skel += skel_tok
    total_saving = (1 - total_skel / max(total_raw, 1)) * 100
    print("-" * 76)
    print(f"{'TOTAL':<40} {total_raw:>12,} {total_skel:>12,} {total_saving:>7.1f}%")


def _estimate_skeleton_tokens(skel: FileSkeleton) -> int:
    lines = len(skel.constants)
    for cls in skel.classes:
        lines += 2 + len(cls.class_vars)
        for fn in cls.methods:
            lines += 2
    for fn in skel.top_level_functions:
        lines += 2
    return max(lines * 8, 40)
