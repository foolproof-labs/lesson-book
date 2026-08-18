"""Tests for mistake classification and daily review."""

from __future__ import annotations

import pytest

from lesson_book.mistakes import (
    add_mistake,
    classify,
    default_rules,
    load_book,
    render_review_markdown,
    review_day,
)


def test_classify_exact_issue_and_category() -> None:
    result = classify("execution_failed", "price_limit")
    assert result["category"] == "price_limit_rejected"
    assert result["priority"] == "P1"
    assert result["rule_id"] == "price_limit"


def test_classify_issue_only_falls_through() -> None:
    result = classify("execution_failed")
    assert result["category"] == "execution_failure"
    assert result["priority"] == "P1"


def test_classify_unknown_is_p2_fail_closed() -> None:
    result = classify("something_new")
    assert result["category"] == "unclassified"
    assert result["priority"] == "P2"
    assert result["rule_id"] == ""


def test_classify_custom_rules_override() -> None:
    rules = [
        {"rule_id": "mine", "issue": "execution_failed", "error_category": None,
         "category": "my_category", "priority": "P0", "action": "stop"}
    ]
    result = classify("execution_failed", rules=rules)
    assert result["category"] == "my_category"
    assert result["priority"] == "P0"


def test_add_mistake_classifies_and_appends(tmp_path) -> None:
    book = tmp_path / "book.jsonl"
    record = add_mistake(
        book,
        title="bought into the gap",
        issue="execution_failed",
        error_category="price_limit",
        date="2026-08-01",
        code="600000",
        industry="banking",
        volatility=0.03,
        tags=("gap",),
        cost=1200.0,
        lesson="never chase the open gap",
    )
    assert record["category"] == "price_limit_rejected"
    assert record["priority"] == "P1"
    assert record["cost"] == pytest.approx(1200.0)
    assert len(load_book(book)) == 1


def test_review_day_groups_and_renders(tmp_path) -> None:
    book = tmp_path / "book.jsonl"
    add_mistake(book, title="m1", issue="execution_failed", error_category="price_limit",
                date="2026-08-01", cost=100.0, lesson="a")
    add_mistake(book, title="m2", issue="execution_failed", date="2026-08-01", cost=50.0, lesson="b")
    add_mistake(book, title="m3", issue="execution_failed", date="2026-08-02", cost=999.0, lesson="c")
    payload = review_day(book, "2026-08-01")
    assert payload["card_count"] == 2
    assert payload["total_cost"] == pytest.approx(150.0)
    assert payload["category_counts"] == {"price_limit_rejected": 1, "execution_failure": 1}
    text = render_review_markdown(payload)
    assert "Tuition review: 2026-08-01" in text
    assert "m1" in text and "m2" in text and "m3" not in text


def test_review_writes_markdown_file(tmp_path) -> None:
    book = tmp_path / "book.jsonl"
    out = tmp_path / "reviews"
    add_mistake(book, title="m1", issue="execution_failed", date="2026-08-01", lesson="a")
    review_day(book, "2026-08-01", out_dir=str(out))
    assert (out / "2026-08-01.md").exists()
    assert "m1" in (out / "2026-08-01.md").read_text(encoding="utf-8")


def test_default_rules_are_copied() -> None:
    rules = default_rules()
    rules[0]["category"] = "mutated"
    assert default_rules()[0]["category"] != "mutated"
