"""Phase 2 — JSON cache with incremental refresh."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from skeleton_extractor.extractor import FileSkeleton, extract

_CACHE_FILE = Path(__file__).parents[2] / ".skeleton_cache" / "skeleton.json"


def _load_cache() -> dict[str, dict]:  # type: ignore[type-arg]
    if _CACHE_FILE.exists():
        return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict[str, dict]) -> None:  # type: ignore[type-arg]
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
    tmp.replace(_CACHE_FILE)


def refresh(src_root: Path, tool_filter: str | None = None) -> dict[str, FileSkeleton]:
    """Re-parse changed files, remove deleted files, return full skeleton map."""
    cache = _load_cache()
    py_files = sorted(src_root.rglob("*.py"))

    if tool_filter:
        tf = tool_filter.lower()
        py_files = [f for f in py_files if tf in (p.lower() for p in f.parts)]

    skeletons: dict[str, FileSkeleton] = {}
    refreshed = 0
    unchanged = 0

    for py_file in py_files:
        key = str(py_file)
        current_hash = _fast_hash(py_file)
        cached = cache.get(key)

        if cached and cached.get("file_hash") == current_hash:
            skeletons[key] = _from_dict(cached)
            unchanged += 1
        else:
            skel = extract(py_file)
            entry = asdict(skel)
            entry["updated_at"] = datetime.now(timezone.utc).isoformat()
            cache[key] = entry
            skeletons[key] = skel
            refreshed += 1

    # remove deleted files
    live_keys = {str(f) for f in py_files}
    stale = [k for k in cache if k not in live_keys]
    for k in stale:
        del cache[k]

    _save_cache(cache)
    print(f"Refreshed {refreshed}/{len(py_files)} files ({unchanged} unchanged)")
    return skeletons


def load_all() -> dict[str, FileSkeleton]:
    """Load full skeleton map from cache without re-parsing."""
    cache = _load_cache()
    return {k: _from_dict(v) for k, v in cache.items()}


def find_uncached(src_root: Path) -> list[Path]:
    """Return .py files on disk that are absent from the cache."""
    cached_keys = set(_load_cache().keys())
    return [f for f in src_root.rglob("*.py") if str(f) not in cached_keys]


def _fast_hash(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _from_dict(d: dict) -> FileSkeleton:  # type: ignore[type-arg]
    from skeleton_extractor.extractor import ClassSkeleton, FunctionSkeleton

    def _fn(f: dict) -> FunctionSkeleton:  # type: ignore[type-arg]
        return FunctionSkeleton(
            name=f["name"],
            signature=f["signature"],
            docstring=f["docstring"],
            decorators=f["decorators"],
            is_private=f["is_private"],
            line_start=f["line_start"],
            line_end=f["line_end"],
            calls=f.get("calls", []),
        )

    def _cls(c: dict) -> ClassSkeleton:  # type: ignore[type-arg]
        return ClassSkeleton(
            name=c["name"],
            docstring=c["docstring"],
            bases=c["bases"],
            class_vars=c["class_vars"],
            methods=[_fn(m) for m in c["methods"]],
            line_start=c["line_start"],
            line_end=c["line_end"],
        )

    return FileSkeleton(
        path=d["path"],
        module_id=d["module_id"],
        srd_id=d["srd_id"],
        tool_code=d["tool_code"],
        classes=[_cls(c) for c in d["classes"]],
        top_level_functions=[_fn(f) for f in d["top_level_functions"]],
        constants=d["constants"],
        file_hash=d["file_hash"],
        imports=d.get("imports", []),
    )
