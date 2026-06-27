"""Investor profile loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PROFILE = {
    "style": "swing_trading",
    "style_zh": "波段操作",
    "risk_level": "medium",
    "max_single_position_pct": 20,
    "preferred_holding_days": "10-60",
}


def load_investor_profile(path: str | Path = "config/investor_profile.json") -> dict[str, Any]:
    profile_path = Path(path)
    if not profile_path.exists():
        return DEFAULT_PROFILE.copy()
    try:
        loaded = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_PROFILE.copy()
    profile = DEFAULT_PROFILE.copy()
    profile.update(loaded)
    return profile
