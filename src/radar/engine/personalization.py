"""Investor profile loading and decision preferences."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_investor_profile(path: str | Path = "config/investor_profile.json") -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
