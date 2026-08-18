"""Tests for lesson records, matching and markdown import."""

from __future__ import annotations

import pytest

from lesson_book.lessons import (
    Lesson,
    import_lessons_markdown,
    load_book,
    match_lessons,
    new_record,
    score_lesson,
)


def test_score_requires_primary_match() -> None:
    lesson = Lesson(title="t", industry="banking")
    assert score_lesson(lesson, "600000", "tech", 0.03) == 0.0


def test_score_weights_and_bonuses() -> None:
    lesson = Lesson(
        title="t",
        code="600000",
        industry="banking",
        volatility=0.03,
        market_cap="large",
        tags=("limit-up", "gap"),
    )
    base = score_lesson(lesson, "600000", "banking", 0.03, market_cap="large")
    assert base == pytest.approx(3.0 + 2.0 + 1.0 + 1.5, abs=1e-9)
    with_tags = score_lesson(
        lesson, "600000", "banking", 0.03, market_cap="large", tags=("limit-up",)
    )
    assert with_tags == pytest.approx(base + 0.5, abs=1e-9)
    # tag bonus is capped at 1.5 (needs >= 3 overlapping tags)
    lesson_many = Lesson(
        title="t", code="600000", industry="banking", volatility=0.03,
        market_cap="large", tags=("limit-up", "gap", "overnight", "volume"),
    )
    with_many = score_lesson(
        lesson_many,
        "600000",
        "banking",
        0.03,
        market_cap="large",
        tags=("limit-up", "gap", "overnight", "volume", "extra"),
    )
    assert with_many == pytest.approx(base + 1.5, abs=1e-9)


def test_volatility_penalty() -> None:
    lesson = Lesson(title="t", code="600000", volatility=0.02)
    close = score_lesson(lesson, "600000", "", 0.025)
    far = score_lesson(lesson, "600000", "", 0.20)
    assert close > far


def test_match_ranks_and_filters(tmp_path) -> None:
    book = tmp_path / "book.jsonl"
    lessons = [
        new_record(title="2026-08-01 gap trap", date="2026-08-01", code="600000",
                   industry="banking", volatility=0.03, tags=("gap",), lesson="wait for retest"),
        new_record(title="2026-07-01 same code lesson", date="2026-07-01", code="600000",
                   industry="banking", volatility=0.03),
        new_record(title="unrelated", date="2026-08-01", code="300033", industry="tech"),
    ]
    for record in lessons:
        book.open("a", encoding="utf-8").write(
            __import__("json").dumps(record, ensure_ascii=False) + "\n"
        )
    matches = match_lessons("600000", "banking", 0.03, tags=("gap",), path=str(book), top_n=3)
    assert len(matches) == 2
    assert matches[0]["code"] == "600000"
    assert matches[0]["score"] > matches[1]["score"]  # tag bonus breaks the tie
    # recency window excludes the July lesson
    recent = match_lessons("600000", "banking", 0.03, path=str(book), top_n=3,
                           days_window=10, now=__import__("datetime").datetime(2026, 8, 5))
    assert len(recent) == 1
    assert recent[0]["date"] == "2026-08-01"


def test_import_markdown_idempotent(tmp_path) -> None:
    md = tmp_path / "lessons.md"
    md.write_text(
        "# Lessons\n"
        "## 2026-08-01 gap trap\n"
        "**Code:** 600000\n"
        "**Industry:** Banking\n"
        "**Volatility:** 0.03\n"
        "**Market Cap:** Large\n"
        "**Tags:** #gap #limit-up\n"
        "**Cost:** 1200\n"
        "**Lesson:** wait for retest\n"
        "body text\n"
        "## 2026-08-02 second\n"
        "**Code:** 300033\n",
        encoding="utf-8",
    )
    book = tmp_path / "book.jsonl"
    first = import_lessons_markdown(md, book)
    second = import_lessons_markdown(md, book)
    assert first == {"imported": 2, "skipped": 0}
    assert second == {"imported": 0, "skipped": 2}
    records = load_book(book)
    assert len(records) == 2
    gap = next(r for r in records if r["title"].startswith("2026-08-01"))
    assert gap["code"] == "600000"
    assert gap["industry"] == "banking"
    assert gap["volatility"] == pytest.approx(0.03)
    assert gap["tags"] == ["#gap", "#limit-up"]
    assert gap["cost"] == pytest.approx(1200.0)
