"""End-to-end CLI tests."""

from __future__ import annotations

import json

import pytest

from lesson_book.cli import main


@pytest.fixture()
def book(tmp_path):
    return str(tmp_path / "book.jsonl")


def test_cli_version() -> None:
    assert main(["version"]) == 0


def test_cli_add_and_match(book) -> None:
    assert (
        main(
            [
                "add",
                "--book", book,
                "--title", "gap trap",
                "--issue", "execution_failed",
                "--error-category", "price_limit",
                "--date", "2026-08-01",
                "--code", "600000",
                "--industry", "banking",
                "--volatility", "0.03",
                "--tags", "gap,limit-up",
                "--cost", "1200",
                "--lesson", "wait for retest",
            ]
        )
        == 0
    )
    assert main(["match", "--book", book, "--industry", "banking", "--volatility", "0.03",
                 "--code", "600000"]) == 0


def test_cli_match_without_hits_returns_1(book) -> None:
    assert main(["match", "--book", book, "--industry", "tech", "--volatility", "0.05"]) == 1


def test_cli_review(book, capsys) -> None:
    main(["add", "--book", book, "--title", "m1", "--issue", "execution_failed",
          "--date", "2026-08-01", "--lesson", "a"])
    capsys.readouterr()  # discard add output
    assert main(["review", "--book", book, "--day", "2026-08-01"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["card_count"] == 1
    assert payload["cards"][0]["category"] == "execution_failure"


def test_cli_import_lessons(tmp_path) -> None:
    md = tmp_path / "lessons.md"
    md.write_text("## 2026-08-01 gap trap\n**Code:** 600000\n**Industry:** Banking\n",
                  encoding="utf-8")
    book = tmp_path / "book.jsonl"
    assert main(["import-lessons", "--from", str(md), "--book", str(book)]) == 0
    assert main(["match", "--book", str(book), "--industry", "banking",
                 "--volatility", "0.03", "--code", "600000"]) == 0
