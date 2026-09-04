"""Tuition memory: a local-first, deterministic mistake ledger.

Record what each mistake cost you, tag it, and let ``match`` remind you of
it the next time the same situation shows up —before you act.  No LLM, no
cloud, no statistics: just an append-only JSONL book and deterministic
scoring, so the reminder is reproducible and auditable.
"""

from .lessons import import_lessons_markdown, match_lessons, score_lesson
from .mistakes import (
    add_mistake,
    classify,
    default_rules,
    load_book,
    review_day,
)

__version__ = "0.1.2"

__all__ = [
    "add_mistake",
    "classify",
    "default_rules",
    "import_lessons_markdown",
    "load_book",
    "match_lessons",
    "review_day",
    "score_lesson",
]

