"""
Module: MD-SCR-014.008.M20 — ai_model_store.py
Parent SRD: SRD-SCR-014.008

Persistent JSON store for user-defined custom AI models + shared validate helper.
Storage: ~/.usswing/ai_models.json
Built-in presets are NOT stored here — they come from _cloud_ai_models.py.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

_APP_DIR = Path.home() / ".usswing"
_STORE_FILE = _APP_DIR / "ai_models.json"


@dataclass
class CustomAIModel:
    tier: str        # "Free" or "Paid"
    provider: str
    name: str
    model_id: str
    tool_use: bool = True


def load_custom_models() -> list[CustomAIModel]:
    if not _STORE_FILE.exists():
        return []
    try:
        data = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [
            CustomAIModel(
                tier=str(r.get("tier", "Paid")),
                provider=str(r.get("provider", "")),
                name=str(r.get("name", "")),
                model_id=str(r.get("model_id", "")),
                tool_use=bool(r.get("tool_use", True)),
            )
            for r in data
            if isinstance(r, dict) and r.get("model_id")
        ]
    except (json.JSONDecodeError, TypeError):
        return []


def save_custom_models(models: list[CustomAIModel]) -> None:
    _APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _STORE_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps([asdict(m) for m in models], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(_STORE_FILE)


def all_model_rows() -> list[tuple[str, str, str, str, bool, bool]]:
    """Return (tier, provider, name, model_id, tool_use, is_custom) for every model."""
    from us_swing.screener.screeners._cloud_ai_models import ALL_MODEL_PRESETS
    rows: list[tuple[str, str, str, str, bool, bool]] = []
    for tier, label, mid, tools in ALL_MODEL_PRESETS:
        provider = mid.split("/")[0].replace("-", " ").title() if "/" in mid else ""
        rows.append((tier, provider, label.split("(")[0].strip(), mid, tools, False))
    for m in load_custom_models():
        rows.append((m.tier, m.provider, m.name, m.model_id, m.tool_use, True))
    return rows


def validate_model(model_id: str, api_key: str = "") -> tuple[bool, str]:
    """Send a 1-token probe to OpenRouter. Returns (ok, message). Thread-safe.

    ``api_key`` overrides the keychain value so callers can pass the key
    currently typed in the dialog before it has been saved.
    """
    try:
        from us_swing.screener.screeners._api_key_store import load as _load_key
        from us_swing.screener.screeners._cloud_ai_models import OPENROUTER_BASE
        import openai as _openai
        resolved_key = api_key.strip() or _load_key()
        if not resolved_key:
            return False, "No API key — enter your OpenRouter key in the API Key field."
        api_key = resolved_key
        client = _openai.OpenAI(
            api_key=resolved_key,
            base_url=OPENROUTER_BASE,
            timeout=15.0,
            default_headers={
                "HTTP-Referer":       "https://github.com/usswing",
                "X-OpenRouter-Title": "USSwing Screener",
            },
        )
        resp = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        if resp.choices:
            return True, "available"
        return False, "empty response from model"
    except Exception as exc:
        # 429 from the upstream provider means the model exists but is
        # temporarily rate-limited — treat as valid, not a hard failure.
        status = getattr(exc, "status_code", None)
        if status == 429:
            return True, "rate-limited by provider — model is valid, retry shortly"
        return False, str(exc)
