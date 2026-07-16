"""Copy safety checks for AI Stock Radar user-facing decision pages.

This module intentionally separates product-facing copy from engineering,
diagnostics, and release-note language. The home page may call the guard for
content that appears above the footer diagnostics area.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

APP_VERSION = "v3.13.0"
RELEASE_NAME = "Decision-first UX"

BANNED_MAIN_COPY: tuple[str, ...] = (
    "本版將 UI",
    "Responsive Decision UX",
    "資料來源、診斷與版本資訊已移至頁尾",
    "Supabase",
    "測試 Supabase",
    "籌碼資料基礎檢查",
    "重新產生今日決策資料",
    "有官方三大法人資料就納入",
    "沒有就明確說明不以籌碼面加分",
)

SAFE_REPLACEMENTS: dict[str, str] = {
    "重新產生今日決策資料": "更新今日資料",
    "測試 Supabase 連線": "資料庫連線檢查",
    "測試 Supabase": "資料庫連線檢查",
    "Supabase": "資料庫",
    "Responsive Decision UX": "今日決策",
    "本版將 UI 收斂成四個核心頁": "今天先看可操作清單與持股風險",
    "資料來源、診斷與版本資訊已移至頁尾": "先處理持股風險，再看今日可操作清單",
    "籌碼資料基礎檢查": "籌碼資料狀態",
}


@dataclass(frozen=True)
class CopyCheckResult:
    clean: bool
    banned_terms: tuple[str, ...]


def find_banned_main_copy(text: str, banned_terms: Iterable[str] = BANNED_MAIN_COPY) -> tuple[str, ...]:
    """Return banned phrases found in text."""
    haystack = text or ""
    return tuple(term for term in banned_terms if term and term in haystack)


def check_main_copy(text: str) -> CopyCheckResult:
    terms = find_banned_main_copy(text)
    return CopyCheckResult(clean=not terms, banned_terms=terms)


def assert_clean_main_copy(text: str, context: str = "main") -> None:
    """Raise a ValueError if engineering copy leaks into the main decision UI."""
    result = check_main_copy(text)
    if not result.clean:
        terms = "、".join(result.banned_terms)
        raise ValueError(f"{context} 出現不應顯示在使用者主畫面的文字：{terms}")


def sanitize_user_facing_copy(text: str, fallback: str = "") -> str:
    """Replace known engineering wording with user-facing wording.

    The function is deliberately conservative. It does not invent investment
    advice; it only removes or replaces product-development language.
    """
    if text is None:
        return fallback
    cleaned = str(text)
    for source, target in SAFE_REPLACEMENTS.items():
        cleaned = cleaned.replace(source, target)
    if find_banned_main_copy(cleaned):
        return fallback
    return cleaned.strip() or fallback
