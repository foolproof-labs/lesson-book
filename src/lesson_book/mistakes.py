"""Mistake records: classification rules, add, daily review.

A mistake record is a lesson with a *price tag*: issue, error category,
priority, and the cost you paid.  Classification is a plain rule table
(issue + error-category -> category / priority / proposed action), fully
overridable, so the taxonomy is yours — the tool only ever classifies,
never enforces.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .lessons import append_record, load_book, new_record

DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "action_gap",
        "issue": "execution_without_action_plan",
        "error_category": None,
        "category": "planning_gap",
        "priority": "P1",
        "action": "associate execution records with an action plan; do not "
                 "replay the sample until the linkage exists",
    },
    {
        "rule_id": "price_limit",
        "issue": "execution_failed",
        "error_category": "price_limit",
        "category": "price_limit_rejected",
        "priority": "P1",
        "action": "review price generation; do not keep expanding the order "
                 "while the price is outside the limit",
    },
    {
        "rule_id": "trading_time_closed",
        "issue": "execution_failed",
        "error_category": "trading_time_closed",
        "category": "trading_time_closed",
        "priority": "P1",
        "action": "review the execution window; outside trading hours only "
                 "observe or record",
    },
    {
        "rule_id": "receipt_reader",
        "issue": "execution_failed",
        "error_category": "receipt_reader_error",
        "category": "receipt_reader_error",
        "priority": "P1",
        "action": "fix the receipt reader encoding/threading defect before "
                 "expanding execution",
    },
    {
        "rule_id": "execution_failure",
        "issue": "execution_failed",
        "error_category": None,
        "category": "execution_failure",
        "priority": "P1",
        "action": "keep the sample, pause expansion; review the instruction "
                 "text, account state and returned receipt",
    },
]


def default_rules() -> list[dict[str, Any]]:
    """Return a deep copy of the default rule table."""
    return [dict(rule) for rule in DEFAULT_RULES]


def classify(
    issue: str,
    error_category: str | None = None,
    rules: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Classify an issue through the rule table (fail-closed to P2).

    Returns ``{"category": ..., "priority": ..., "action": ...}``.  First
    matching rule wins: exact issue + error_category match beats exact issue
    alone.
    """
    rules = rules if rules is not None else DEFAULT_RULES
    issue = str(issue or "")
    error_category = str(error_category or "") or None

    for rule in rules:
        expected_issue = rule.get("issue")
        expected_category = rule.get("error_category") or None
        if expected_issue != issue:
            continue
        if expected_category is not None and expected_category != error_category:
            continue
        return {
            "category": str(rule.get("category") or "unclassified"),
            "priority": str(rule.get("priority") or "P2"),
            "action": str(rule.get("action") or ""),
            "rule_id": str(rule.get("rule_id") or ""),
        }
    # exact issue match without error-category requirement, if any
    for rule in rules:
        if rule.get("issue") == issue and not rule.get("error_category"):
            return {
                "category": str(rule.get("category") or "unclassified"),
                "priority": str(rule.get("priority") or "P2"),
                "action": str(rule.get("action") or ""),
                "rule_id": str(rule.get("rule_id") or ""),
            }
    return {
        "category": "unclassified",
        "priority": "P2",
        "action": "review manually and extend the rule table",
        "rule_id": "",
    }


def add_mistake(
    book_path: Path | str,
    *,
    title: str,
    issue: str,
    error_category: str | None = None,
    date: str | None = None,
    code: str = "",
    industry: str = "",
    volatility: float | None = None,
    market_cap: str = "",
    tags: tuple[str, ...] = (),
    cost: float | None = None,
    lesson: str = "",
    situation: str = "",
    rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Classify and append one mistake record; returns the record."""
    classification = classify(issue, error_category, rules)
    day = date or datetime.now().strftime("%Y-%m-%d")
    record = new_record(
        title=title,
        date=day,
        code=code,
        industry=industry,
        volatility=volatility,
        market_cap=market_cap,
        tags=tags,
        category=classification["category"],
        priority=classification["priority"],
        cost=cost,
        lesson=lesson or classification["action"],
        situation=situation,
    )
    record["issue"] = issue
    record["error_category"] = error_category
    append_record(book_path, record)
    return record


def review_day(
    book_path: Path | str,
    day: str,
    *,
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Build a daily review of the mistakes recorded on ``day``.

    Writes ``YYYY-MM-DD.md`` when ``out_dir`` is given; always returns the
    payload (counts by category and priority, total cost, cards).
    """
    records = [r for r in load_book(book_path) if str(r.get("date"))[:10] == day]
    cards = [
        {
            "record_id": r.get("record_id", ""),
            "title": r.get("title", ""),
            "issue": r.get("issue", ""),
            "category": r.get("category", ""),
            "priority": r.get("priority", ""),
            "cost": r.get("cost"),
            "lesson": r.get("lesson", ""),
            "tags": r.get("tags", []),
        }
        for r in records
    ]
    category_counts = Counter(card["category"] for card in cards)
    priority_counts = Counter(card["priority"] for card in cards)
    total_cost = sum(card["cost"] for card in cards if isinstance(card["cost"], (int, float)))
    payload = {
        "day": day,
        "card_count": len(cards),
        "category_counts": dict(category_counts),
        "priority_counts": dict(priority_counts),
        "total_cost": round(total_cost, 4) if total_cost else None,
        "cards": cards,
    }
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{day}.md").write_text(render_review_markdown(payload), encoding="utf-8")
    return payload


def render_review_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Tuition review: {payload['day']}",
        "",
        f"- mistakes: {payload['card_count']}",
        f"- total cost: {payload['total_cost'] if payload['total_cost'] is not None else '-'}",
        "",
        "## By category",
        "",
    ]
    for key, value in sorted(payload["category_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## By priority", ""]
    for key, value in sorted(payload["priority_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Cards", ""]
    if not payload["cards"]:
        lines.append("- no mistakes recorded this day.")
    for card in payload["cards"]:
        lines.extend(
            [
                f"### {card['title']}",
                "",
                f"- issue: {card['issue']}",
                f"- category: {card['category']} ({card['priority']})",
                f"- cost: {card['cost'] if card['cost'] is not None else '-'}",
                f"- lesson: {card['lesson'] or '-'}",
                "",
            ]
        )
    lines.append("This review classifies and records; it changes no rules, "
                 "positions, risk limits or execution permissions.")
    return "\n".join(lines)
