"""AI Stock Radar Streamlit entrypoint for v3.13.0 Decision-first UX."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> None:
    import streamlit as st

    from radar.ui.decision_data_adapter import build_dashboard_view, load_dashboard_payload
    from radar.ui.decision_first_home import render_home_page

    st.set_page_config(
        page_title="AI Stock Radar｜今日決策",
        page_icon="🚀",
        layout="wide",
    )

    payload = load_dashboard_payload(ROOT / "output" / "dashboard_data.json")
    view = build_dashboard_view(payload)
    render_home_page(view=view, snapshot_time="盤中")


if __name__ == "__main__":
    main()
