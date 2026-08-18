"""Command-line interface for lesson-book.

Subcommands:

- ``add``             record a mistake (classified via the rule table)
- ``import-lessons``  parse a ``##``-style markdown knowledge base into the book
- ``match``           rank lessons relevant to a current situation (pre-action)
- ``review``          daily review markdown of one day's mistakes
- ``version``         print version
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .lessons import import_lessons_markdown, match_lessons
from .mistakes import add_mistake, review_day


def _print_json(body: Any) -> None:
    print(json.dumps(body, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lb",
        description="Tuition memory: a local-first, deterministic mistake ledger.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="record a mistake")
    add.add_argument("--book", required=True, help="JSONL book path")
    add.add_argument("--title", required=True)
    add.add_argument("--issue", required=True)
    add.add_argument("--error-category", default=None)
    add.add_argument("--date", default=None)
    add.add_argument("--code", default="")
    add.add_argument("--industry", default="")
    add.add_argument("--volatility", type=float, default=None)
    add.add_argument("--market-cap", default="")
    add.add_argument("--tags", default="", help="comma-separated tags")
    add.add_argument("--cost", type=float, default=None)
    add.add_argument("--lesson", default="")
    add.add_argument("--situation", default="")

    imp = sub.add_parser("import-lessons", help="import a markdown knowledge base")
    imp.add_argument("--from", dest="from_path", required=True, help="markdown lessons file")
    imp.add_argument("--book", required=True, help="JSONL book path")

    match = sub.add_parser("match", help="match the current situation against the book")
    match.add_argument("--book", required=True)
    match.add_argument("--code", default="")
    match.add_argument("--industry", required=True)
    match.add_argument("--volatility", type=float, required=True)
    match.add_argument("--market-cap", default="")
    match.add_argument("--tags", default="", help="comma-separated tags")
    match.add_argument("--top-n", type=int, default=3)
    match.add_argument("--days-window", type=int, default=None)

    review = sub.add_parser("review", help="daily review of one day's mistakes")
    review.add_argument("--book", required=True)
    review.add_argument("--day", required=True, help="YYYY-MM-DD")
    review.add_argument("--out", default=None, help="output directory for the markdown")

    sub.add_parser("version", help="print version")
    return parser


def _split_tags(value: str) -> tuple[str, ...]:
    return tuple(tag.strip() for tag in value.split(",") if tag.strip())


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        print(__version__)
        return 0

    if args.command == "add":
        record = add_mistake(
            args.book,
            title=args.title,
            issue=args.issue,
            error_category=args.error_category,
            date=args.date,
            code=args.code,
            industry=args.industry,
            volatility=args.volatility,
            market_cap=args.market_cap,
            tags=_split_tags(args.tags),
            cost=args.cost,
            lesson=args.lesson,
            situation=args.situation,
        )
        _print_json(record)
        return 0

    if args.command == "import-lessons":
        result = import_lessons_markdown(args.from_path, args.book)
        print(f"import: {result['imported']} imported, {result['skipped']} skipped")
        return 0

    if args.command == "match":
        matches = match_lessons(
            args.code,
            args.industry,
            args.volatility,
            market_cap=args.market_cap,
            tags=_split_tags(args.tags),
            top_n=args.top_n,
            path=args.book,
            days_window=args.days_window,
        )
        if not matches:
            print("match: no relevant lessons (this situation is new tuition)")
            return 1
        _print_json({"matches": matches})
        return 0

    if args.command == "review":
        payload = review_day(args.book, args.day, out_dir=args.out)
        _print_json(payload)
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
