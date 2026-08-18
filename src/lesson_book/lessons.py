"""Lesson records and deterministic situation matching.

A lesson record carries the context in which the tuition was paid: code,
industry, volatility, market cap and tags.  ``match_lessons`` scores the
current situation against every record and returns the most relevant ones,
so the book can speak up *before* a decision instead of after it.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "lesson_book.lesson.v1"

CODE_WEIGHT = 3.0
INDUSTRY_WEIGHT = 2.0
MARKET_CAP_WEIGHT = 1.0
VOLATILITY_BONUS_BASE = 1.5
VOLATILITY_PENALTY_RATE = 5.0
TAG_WEIGHT = 0.5
TAG_BONUS_CAP = 1.5


@dataclass(frozen=True)
class Lesson:
    """One tuition record."""

    title: str
    code: str = ""
    industry: str = ""
    volatility: float | None = None
    market_cap: str = ""
    date: str = ""
    tags: tuple[str, ...] = ()
    category: str = ""
    priority: str = ""
    cost: float | None = None
    lesson: str = ""
    raw: str = ""


def new_record(
    *,
    title: str,
    date: str,
    code: str = "",
    industry: str = "",
    volatility: float | None = None,
    market_cap: str = "",
    tags: tuple[str, ...] = (),
    category: str = "",
    priority: str = "",
    cost: float | None = None,
    lesson: str = "",
    situation: str = "",
) -> dict[str, Any]:
    """Build one record dict ready to append to the book."""
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": str(uuid.uuid4()),
        "title": title,
        "date": date,
        "code": code,
        "industry": (industry or "").lower(),
        "volatility": volatility,
        "market_cap": (market_cap or "").lower(),
        "tags": list(tags),
        "category": category,
        "priority": priority,
        "cost": cost,
        "lesson": lesson,
        "situation": situation,
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def load_book(path: Path | str) -> list[dict[str, Any]]:
    """Load the JSONL book; corrupt lines raise with their line number."""
    path = Path(path)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"book_corrupt:{path}:{line_no}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"book_not_object:{path}:{line_no}")
        records.append(payload)
    return records


def append_record(path: Path | str, record: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _record_to_lesson(record: dict[str, Any]) -> Lesson:
    return Lesson(
        title=str(record.get("title") or ""),
        code=str(record.get("code") or ""),
        industry=str(record.get("industry") or "").lower(),
        volatility=_as_float(record.get("volatility")),
        market_cap=str(record.get("market_cap") or "").lower(),
        date=str(record.get("date") or "")[:10],
        tags=tuple(str(tag) for tag in (record.get("tags") or [])),
        category=str(record.get("category") or ""),
        priority=str(record.get("priority") or ""),
        cost=_as_float(record.get("cost")),
        lesson=str(record.get("lesson") or ""),
        raw=json.dumps(record, ensure_ascii=False),
    )


def _as_float(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value == value else None  # NaN -> None


def score_lesson(
    lesson: Lesson,
    code: str,
    industry: str,
    volatility: float,
    market_cap: str = "",
    tags: tuple[str, ...] = (),
) -> float:
    """Deterministic relevance score for a current situation.

    Primary match (code/industry/market cap) is required for a non-zero
    score; volatility proximity and tag overlap add bonuses.
    """
    score = 0.0
    has_primary_match = False
    if lesson.code and lesson.code == code:
        score += CODE_WEIGHT
        has_primary_match = True
    if lesson.industry and lesson.industry == industry.lower():
        score += INDUSTRY_WEIGHT
        has_primary_match = True
    if lesson.market_cap and market_cap and lesson.market_cap == market_cap.lower():
        score += MARKET_CAP_WEIGHT
        has_primary_match = True
    if not has_primary_match:
        return 0.0
    if lesson.volatility is not None:
        score += max(0.0, VOLATILITY_BONUS_BASE - abs(lesson.volatility - volatility) * VOLATILITY_PENALTY_RATE)
    if tags and lesson.tags:
        overlap = len(set(tags) & set(lesson.tags))
        if overlap:
            score += min(TAG_BONUS_CAP, overlap * TAG_WEIGHT)
    return score


def match_lessons(
    code: str,
    industry: str,
    volatility: float,
    market_cap: str = "",
    tags: tuple[str, ...] = (),
    top_n: int = 3,
    path: Path | str = "lesson-book.jsonl",
    days_window: int | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Rank the most relevant lessons for the current situation.

    ``days_window`` filters to records no older than N days (None = no
    filter).  Returns the top matches with scores, so a pre-action hook can
    surface them.
    """
    now = now or datetime.now()
    ranked: list[tuple[float, Lesson]] = []
    for record in load_book(path):
        lesson = _record_to_lesson(record)
        if days_window is not None and lesson.date:
            try:
                lesson_date = datetime.strptime(lesson.date, "%Y-%m-%d")
            except ValueError:
                lesson_date = None
            if lesson_date is not None and (now - lesson_date).days > days_window:
                continue
        score = score_lesson(lesson, code, industry, volatility, market_cap, tags)
        if score > 0:
            ranked.append((score, lesson))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "title": lesson.title,
            "score": round(score, 3),
            "code": lesson.code,
            "industry": lesson.industry,
            "tags": list(lesson.tags),
            "category": lesson.category,
            "priority": lesson.priority,
            "cost": lesson.cost,
            "lesson": lesson.lesson,
            "date": lesson.date,
        }
        for score, lesson in ranked[:top_n]
    ]


# --------------------------------------------------------------------------- #
# Markdown knowledge-base import (##-headed lessons file)
# --------------------------------------------------------------------------- #
def _field(block: str, name: str) -> str:
    match = re.search(rf"\*\*{re.escape(name)}:\*\*\s*(.+)", block)
    return match.group(1).strip() if match else ""


def import_lessons_markdown(
    markdown_path: Path | str,
    book_path: Path | str,
) -> dict[str, Any]:
    """Parse ``## Title`` lessons with ``**Field:**`` metadata into the book.

    Recognized fields: Code, Industry, Volatility, Market Cap, Tags
    (``#tag`` words), Cost, Lesson, Category, Priority.  Existing titles in
    the book are skipped (idempotent).
    """
    path = Path(markdown_path)
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    chunks = re.split(r"\n(?=##\s+)", text)
    existing = {str(r.get("title")) for r in load_book(book_path)}
    imported = 0
    skipped = 0
    for chunk in chunks:
        title_match = re.search(r"^##\s+(.+)", chunk, re.MULTILINE)
        if not title_match:
            continue
        title_text = title_match.group(1).strip()
        if title_text in existing:
            skipped += 1
            continue
        date_text = ""
        date_match = re.match(r"^(\d{4}-\d{2}-\d{2})\b", title_text)
        if date_match:
            date_text = date_match.group(1)
        volatility_text = _field(chunk, "Volatility")
        try:
            volatility = float(volatility_text) if volatility_text else None
        except ValueError:
            volatility = None
        cost_text = _field(chunk, "Cost")
        try:
            cost = float(cost_text) if cost_text else None
        except ValueError:
            cost = None
        record = new_record(
            title=title_text,
            date=date_text,
            code=_field(chunk, "Code"),
            industry=_field(chunk, "Industry"),
            volatility=volatility,
            market_cap=_field(chunk, "Market Cap"),
            tags=tuple(re.findall(r"#[\w-]+", _field(chunk, "Tags"))),
            category=_field(chunk, "Category"),
            priority=_field(chunk, "Priority"),
            cost=cost,
            lesson=_field(chunk, "Lesson"),
        )
        append_record(book_path, record)
        imported += 1
    return {"imported": imported, "skipped": skipped}
