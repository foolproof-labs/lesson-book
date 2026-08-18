"""End-to-end demo: record -> import -> match -> review on a scratch book.

Run with:  python examples/demo.py
Writes a scratch book under a temporary directory; safe to re-run.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lesson_book.cli import main as cli_main  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="lb-demo-"))
BOOK = TMP / "book.jsonl"


def _run(label: str, argv: list[str]) -> None:
    print(f"\n== {label} ==")
    code = cli_main(argv)
    print(f"=> exit code: {code}")


def main() -> int:
    _run(
        "1. record a mistake (classified P1: price_limit_rejected)",
        [
            "add",
            "--book", str(BOOK),
            "--title", "bought into the open gap",
            "--issue", "execution_failed",
            "--error-category", "price_limit",
            "--date", "2026-08-01",
            "--code", "600000",
            "--industry", "banking",
            "--volatility", "0.03",
            "--tags", "gap,limit-up",
            "--cost", "1200",
            "--lesson", "never chase the open gap; wait for the retest",
        ],
    )

    lessons_md = TMP / "lessons.md"
    lessons_md.write_text(
        "# Lessons\n"
        "## 2026-07-15 chased the limit-up open\n"
        "**Code:** 000001\n"
        "**Industry:** Banking\n"
        "**Volatility:** 0.02\n"
        "**Tags:** #limit-up #gap\n"
        "**Cost:** 800\n"
        "**Lesson:** the open gap after limit-up is a trap; wait for volume confirmation\n",
        encoding="utf-8",
    )
    _run(
        "2. import a markdown knowledge base",
        ["import-lessons", "--from", str(lessons_md), "--book", str(BOOK)],
    )

    _run(
        "3. tomorrow's situation: same industry, similar volatility (pre-action)",
        [
            "match",
            "--book", str(BOOK),
            "--industry", "banking",
            "--volatility", "0.025",
            "--code", "600000",
            "--tags", "gap",
            "--top-n", "3",
        ],
    )

    _run("4. daily review", ["review", "--book", str(BOOK), "--day", "2026-08-01"])

    print(f"\nbook written to: {BOOK}")
    print("book lines:", len(BOOK.read_text(encoding="utf-8").splitlines()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
