"""Module: MD-SCR-005.001.M12 — screener/manager.py
Parent SRD: SRD-SCR-005.001–008, SRD-SCR-005.004

PresetManager — CRUD + permission management for Preset definitions on disk.
Handles create/load/list/update/delete and grant/revoke access.
List methods accept an optional style_filter (SRD-005.004).
Supports v1 migration (legacy ScreenerConfig → Preset).
"""
from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from us_swing.screener.base import PresetAccessDenied, PresetNotFoundError
from us_swing.screener.preset import Preset, PresetType, ScreenerRef, _VALID_STYLES

_log = logging.getLogger(__name__)

_VALID_STYLE_FILTERS: frozenset[str] = _VALID_STYLES


class PresetManager:
    """CRUD + permissions for Preset definitions on disk.

    Directory layout (all relative to *base_dir*):
        presets_admin/                → admin preset JSON files
        presets_user/{user_id}/       → per-user preset JSON files
        preset_{id}/                  → execution results (deleted by delete_preset)
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or Path.home() / ".usswing" / "screener_results"

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _admin_dir(self) -> Path:
        return self._base / "presets_admin"

    def _user_dir(self, user_id: str) -> Path:
        return self._base / "presets_user" / user_id

    def _admin_path(self, preset_id: str) -> Path:
        return self._admin_dir() / f"{preset_id}.json"

    def _user_path(self, user_id: str, preset_id: str) -> Path:
        return self._user_dir(user_id) / f"{preset_id}.json"

    def _results_dir(self, preset_id: str) -> Path:
        return self._base / f"preset_{preset_id}"

    # ------------------------------------------------------------------
    # Internal I/O
    # ------------------------------------------------------------------

    def _write(self, path: Path, preset: Preset) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(preset.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(path)

    def _read(self, path: Path) -> Preset:
        return Preset.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _resolve_path(self, preset_id: str, preset: Preset) -> Path:
        """Return the on-disk path for an already-loaded preset."""
        if preset.is_admin:
            return self._admin_path(preset_id)
        user_base = self._base / "presets_user"
        if user_base.exists():
            for ud in user_base.iterdir():
                if ud.is_dir():
                    candidate = ud / f"{preset_id}.json"
                    if candidate.exists():
                        return candidate
        return self._user_path(preset.created_by or preset_id, preset_id)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_preset(
        self,
        preset: Preset,
        user_id: str,
        is_admin_user: bool = False,
    ) -> Path:
        """Persist a new preset and return its file path.

        Raises:
            PresetAccessDenied: if preset.is_admin is True but is_admin_user is False.
        """
        if preset.is_admin and not is_admin_user:
            raise PresetAccessDenied(
                f"User '{user_id}' is not an admin and cannot create admin presets."
            )
        now = datetime.now(timezone.utc)
        preset.created_by = user_id
        preset.created_at = now
        preset.updated_at = now

        path = self._admin_path(preset.id) if preset.is_admin else self._user_path(user_id, preset.id)
        self._write(path, preset)
        return path

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_preset(self, preset_id: str, user_id: str) -> Preset:
        """Load a preset by ID, enforcing access control.

        Access rules:
        - Admin presets are accessible by any user.
        - User presets are accessible by their creator or those in assigned_to.

        Raises:
            PresetNotFoundError: if the preset cannot be found.
            PresetAccessDenied: if the requesting user lacks access.
        """
        admin_path = self._admin_path(preset_id)
        if admin_path.exists():
            return self._read(admin_path)

        own_path = self._user_path(user_id, preset_id)
        if own_path.exists():
            return self._read(own_path)

        user_base = self._base / "presets_user"
        if user_base.exists():
            for ud in user_base.iterdir():
                if not ud.is_dir():
                    continue
                candidate = ud / f"{preset_id}.json"
                if candidate.exists():
                    preset = self._read(candidate)
                    if user_id in preset.assigned_to:
                        return preset
                    raise PresetAccessDenied(
                        f"User '{user_id}' does not have access to preset '{preset_id}'."
                    )

        raise PresetNotFoundError(f"Preset '{preset_id}' not found.")

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_admin_presets(self, style_filter: str | None = None) -> list[Preset]:
        """Return all admin presets, optionally filtered by trading style.

        Args:
            style_filter: one of ``"swing"``, ``"day"``, ``"position"``, or ``None``
                (returns all). Untagged presets (``trading_styles=[]``) always pass.

        Raises:
            ValueError: if *style_filter* is not a recognised style value.
        """
        admin_dir = self._admin_dir()
        if not admin_dir.exists():
            return _apply_style_filter([], style_filter)
        presets = [
            self._read(p)
            for p in sorted(admin_dir.glob("*.json"))
            if not p.name.endswith(".tmp")
        ]
        return _apply_style_filter(presets, style_filter)

    def list_user_presets(self, user_id: str, style_filter: str | None = None) -> list[Preset]:
        """Return all presets accessible to user_id (own + shared), optionally filtered.

        Args:
            user_id: requesting user.
            style_filter: one of ``"swing"``, ``"day"``, ``"position"``, or ``None``
                (returns all). Untagged presets (``trading_styles=[]``) always pass.

        Raises:
            ValueError: if *style_filter* is not a recognised style value.
        """
        presets: list[Preset] = []

        user_dir = self._user_dir(user_id)
        if user_dir.exists():
            for p in sorted(user_dir.glob("*.json")):
                if not p.name.endswith(".tmp"):
                    presets.append(self._read(p))

        user_base = self._base / "presets_user"
        if user_base.exists():
            for od in user_base.iterdir():
                if not od.is_dir() or od.name == user_id:
                    continue
                for p in sorted(od.glob("*.json")):
                    if p.name.endswith(".tmp"):
                        continue
                    preset = self._read(p)
                    if user_id in preset.assigned_to:
                        presets.append(preset)

        return _apply_style_filter(presets, style_filter)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_preset(self, preset_id: str, updates: dict[str, Any], user_id: str) -> Preset:
        """Apply *updates* dict to a preset and persist.

        Raises:
            PresetAccessDenied: if user_id is not the creator.
            PresetNotFoundError: if the preset cannot be found.
        """
        preset = self._find_writable(preset_id, user_id)
        for key, value in updates.items():
            if hasattr(preset, key):
                setattr(preset, key, value)
        preset.updated_at = datetime.now(timezone.utc)
        self._write(self._resolve_path(preset_id, preset), preset)
        return preset

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_preset(self, preset_id: str, user_id: str) -> None:
        """Delete a preset file and its associated results directory.

        Raises:
            PresetAccessDenied: if user_id is not the creator.
            PresetNotFoundError: if the preset cannot be found.
        """
        preset = self._find_writable(preset_id, user_id)
        path = self._resolve_path(preset_id, preset)
        if path.exists():
            path.unlink()

        results = self._results_dir(preset_id)
        if results.exists():
            shutil.rmtree(results)

    # ------------------------------------------------------------------
    # Access control
    # ------------------------------------------------------------------

    def grant_access(self, preset_id: str, user_ids: list[str], requester_id: str) -> Preset:
        """Add *user_ids* to preset.assigned_to.

        Raises:
            PresetAccessDenied: if requester_id is not the creator.
        """
        preset = self._find_writable(preset_id, requester_id)
        for uid in user_ids:
            if uid not in preset.assigned_to:
                preset.assigned_to.append(uid)
        preset.updated_at = datetime.now(timezone.utc)
        self._write(self._resolve_path(preset_id, preset), preset)
        return preset

    def revoke_access(self, preset_id: str, user_id: str, requester_id: str) -> Preset:
        """Remove *user_id* from preset.assigned_to.

        Raises:
            PresetAccessDenied: if requester_id is not the creator.
        """
        preset = self._find_writable(preset_id, requester_id)
        preset.assigned_to = [u for u in preset.assigned_to if u != user_id]
        preset.updated_at = datetime.now(timezone.utc)
        self._write(self._resolve_path(preset_id, preset), preset)
        return preset

    # ------------------------------------------------------------------
    # v1 Migration
    # ------------------------------------------------------------------

    def migrate_v1_presets(self, user_id: str, v1_config: dict[str, Any]) -> Preset:
        """Create a user preset from a legacy v1 ScreenerConfig dict.

        Wraps the v1 config in a single IndicatorScreener reference.
        """
        preset_id = v1_config.get("id") or str(uuid.uuid4())
        name = v1_config.get("name", f"Migrated ({preset_id[:8]})")
        ref = ScreenerRef(
            screener_id="indicator_composite",
            enabled=True,
            weight=1.0,   # required for weighted executor logic
            config=v1_config,
        )
        now = datetime.now(timezone.utc)
        preset = Preset(
            id=preset_id,
            name=name,
            preset_type=PresetType.WEIGHTED,
            screeners=[ref],
            threshold=0.5,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self._write(self._user_path(user_id, preset_id), preset)
        return preset

    # ------------------------------------------------------------------
    # Internal: find a preset that *user_id* is allowed to write
    # ------------------------------------------------------------------

    def _find_writable(self, preset_id: str, user_id: str) -> Preset:
        """Return the preset if user_id is its creator; raise otherwise."""
        admin_path = self._admin_path(preset_id)
        if admin_path.exists():
            preset = self._read(admin_path)
            if preset.created_by != user_id:
                raise PresetAccessDenied(
                    f"User '{user_id}' is not the creator of preset '{preset_id}'."
                )
            return preset

        own_path = self._user_path(user_id, preset_id)
        if own_path.exists():
            return self._read(own_path)

        user_base = self._base / "presets_user"
        if user_base.exists():
            for ud in user_base.iterdir():
                if not ud.is_dir():
                    continue
                candidate = ud / f"{preset_id}.json"
                if candidate.exists():
                    preset = self._read(candidate)
                    if preset.created_by == user_id:
                        return preset
                    raise PresetAccessDenied(
                        f"User '{user_id}' is not the creator of preset '{preset_id}'."
                    )

        raise PresetNotFoundError(f"Preset '{preset_id}' not found.")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _apply_style_filter(presets: list[Preset], style_filter: str | None) -> list[Preset]:
    """Filter *presets* by trading style.

    Untagged presets (``trading_styles == []``) always pass regardless of filter.

    Raises:
        ValueError: if *style_filter* is not in ``_VALID_STYLE_FILTERS``.
    """
    if style_filter is None:
        return presets
    if style_filter not in _VALID_STYLE_FILTERS:
        raise ValueError(
            f"Unknown style_filter: {style_filter!r}. "
            f"Valid values: {sorted(_VALID_STYLE_FILTERS)}."
        )
    return [p for p in presets if not p.trading_styles or style_filter in p.trading_styles]
