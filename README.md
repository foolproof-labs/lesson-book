# lesson-book

![PyPI version](https://img.shields.io/pypi/v/lesson-book.svg)
![PyPI downloads](https://img.shields.io/pypi/dm/lesson-book.svg)
![CI](https://github.com/foolproof-labs/lesson-book/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

## 中文说明

`lesson-book` 是本地优先、可复现的交易经验记录工具，也可以用于 A 股研究
和模拟交易流程。它记录错误、代价和标签，并在相似情境再次出现时给出提醒。
匹配规则是固定的，不调用大模型、不上传云端，也不提供买卖建议；它的作用是
让过去的经验在行动前被看见。

**Tuition memory for traders.** A local-first, deterministic mistake ledger:
record what each mistake cost you, tag it, and `lb match` reminds you of it
the next time the same situation shows up —**before** you act. Python
3.11+, **zero dependencies**, Windows / Linux / macOS. No LLM, no cloud, no
statistics: the reminder is reproducible and auditable.

**Status:** v0.1.1 alpha, published on PyPI. The matching logic is distilled from a production
trading system's lesson-matching module; this standalone package is new.

## Why this exists

Your trading system has a memory problem: it forgets. The mistake you paid
1,200 for last month looks like a fresh opportunity today, because nothing
stood between the idea and the order. Trading journals solve the *recording*
half —they are ledgers of what happened. `lesson-book` solves the
*retrieval* half: it keeps the tuition in a form that can speak up when the
same situation appears again.

Two design commitments make it different from journaling apps and LLM
"memory" systems:

1. **Deterministic, not statistical.** Scoring is a fixed weighted formula
   (code +3, industry +2, market cap +1, volatility proximity bonus, tag
   overlap bonus). Same situation, same reminder, every time —the opposite
   of an LLM memory that improvises.
2. **Local-first and verifiable.** The book is a plain append-only JSONL
   file in your repo. `git log` on it *is* your audit trail; nothing ever
   leaves your machine.

## Philosophy

**Tuition is capital —the system does not forget what you paid for, and it
reminds you before you pay again.**

This is the checklist culture of aviation and medicine, applied to trading:
Gawande's [*The Checklist Manifesto*](https://en.wikipedia.org/wiki/The_Checklist_Manifesto)
is the canonical argument that simple checklists reduce catastrophic error
rates by an order of magnitude. And it is the **premortem** in reverse:
[Klein (2007), "Performing a Project Premortem"](https://hbr.org/2007/09/performing-a-project-premortem)
asks you to imagine, before acting, that you already failed and explain why.
`lb match` is the automated premortem: it surfaces the historical answers to
"why will this fail?" without you having to ask.

The [IOM (1999), *To Err Is Human*](https://nap.nationalacademies.org/catalog/9728/to-err-is-human-building-a-safer-health-system)
framing applies directly: errors are a system problem, not a character
flaw. The book exists to improve the system —classification, review and
retrieval —never to punish the person. That is why records carry `cost`
(a number, not a shame) and why the tool classifies but never enforces:
rules, positions and limits stay with you.

## Quick start

```bash
# install the published package from PyPI
pip install lesson-book

# or run without installing anything:
#   PYTHONPATH=src python -m lesson_book --help

python examples/demo.py   # record, match, review on a scratch book
```

Your own book:

```bash
# record a mistake —classification happens via the rule table
lb add --book book.jsonl \
  --title "bought into the open gap" \
  --issue execution_failed --error-category price_limit \
  --date 2026-08-01 --code 600000 --industry banking \
  --volatility 0.03 --tags gap,limit-up --cost 1200 \
  --lesson "never chase the open gap; wait for the retest"

# before acting tomorrow: ask the book
lb match --book book.jsonl --industry banking --volatility 0.03 \
  --code 600000 --tags gap
# -> the 2026-08-01 record, score 8.0, lesson: "never chase the open gap..."

# import an existing ##-style markdown knowledge base
lb import-lessons --from LESSONS.md --book book.jsonl

# daily review of what the day cost
lb review --book book.jsonl --day 2026-08-01 --out reviews/
```

## Commands

| Command | What it does |
| --- | --- |
| `add` | Record a mistake: `--title`, `--issue` (required), `--error-category`, context fields (`--code`, `--industry`, `--volatility`, `--market-cap`, `--tags`), `--cost`, `--lesson`, `--situation`. Classified via the rule table (P1/P2, fail-closed to P2) |
| `import-lessons` | Parse a `##`-headed markdown knowledge base with `**Field:**` metadata (Code/Industry/Volatility/Market Cap/Tags/Cost/Lesson/...) into the book. Idempotent by title |
| `match` | Rank lessons relevant to the current situation; exit 1 when nothing matches (a pre-action hook can fail-closed on it) |
| `review` | Daily review: cards grouped by category and priority, total cost, markdown output |
| `version` | Print version |

## The book

`book.jsonl` —append-only, one JSON record per line:

```json
{"schema_version": "lesson_book.lesson.v1", "record_id": "...",
 "title": "bought into the open gap", "date": "2026-08-01",
 "code": "600000", "industry": "banking", "volatility": 0.03,
 "market_cap": "large", "tags": ["gap", "limit-up"],
 "category": "price_limit_rejected", "priority": "P1",
 "cost": 1200.0, "lesson": "never chase the open gap",
 "situation": "", "recorded_at": "..."}
```

Matching score (deterministic):

| Signal | Weight |
| --- | --- |
| same code | +3.0 |
| same industry | +2.0 |
| same market cap | +1.0 |
| volatility proximity | up to +1.5 (decays 5× the gap) |
| tag overlap | +0.5 per tag, capped at +1.5 |

A primary match (code / industry / market cap) is required for a non-zero
score —the book never speaks up about situations it has no grounds to
compare.

## Classification rules

`add` classifies `issue` + `error_category` through a plain rule table
(`category`, `priority`, `action`), fully overridable in code. Defaults:

| issue | error_category | category | priority |
| --- | --- | --- | --- |
| `execution_without_action_plan` | —| `planning_gap` | P1 |
| `execution_failed` | `price_limit` | `price_limit_rejected` | P1 |
| `execution_failed` | `trading_time_closed` | `trading_time_closed` | P1 |
| `execution_failed` | `receipt_reader_error` | `receipt_reader_error` | P1 |
| `execution_failed` | —| `execution_failure` | P1 |
| anything else | —| `unclassified` | P2 |

Unclassified records are P2 with "review manually and extend the rule table"
—the taxonomy grows with you, never silently.

## Development

```bash
python -m pip install -e . pytest
python -m pytest
```

CI runs the full test suite on Ubuntu, Windows and macOS with Python 3.11
and 3.12. Issues are handled on weekends; pull requests are welcome.

## Related work

- [Klein (2007), Performing a Project Premortem (HBR)](https://hbr.org/2007/09/performing-a-project-premortem) —imagine the failure before it happens
- [Gawande (2009), The Checklist Manifesto](https://en.wikipedia.org/wiki/The_Checklist_Manifesto) —checklists as error-rate reduction
- [IOM (1999), To Err Is Human](https://nap.nationalacademies.org/catalog/9728/to-err-is-human-building-a-safer-health-system) —errors as system problems

## Project family

Part of [Foolproof Labs](https://github.com/foolproof-labs) — a toolchain
against self-deception in quantitative research:

- [pit-adjuster](https://github.com/foolproof-labs/pit-adjuster) — PIT back-adjustment with static forward-adjustment drift detection
- [falsification-ledger](https://github.com/foolproof-labs/falsification-ledger) — pre-registration and falsification ledger
- [factor-qc](https://github.com/foolproof-labs/factor-qc) — fail-closed backtest quality gate
- [lesson-book](https://github.com/foolproof-labs/lesson-book) — tuition memory for traders
- [lookahead-free](https://github.com/foolproof-labs/lookahead-free) — verifiable look-ahead-freedom checks
- [ashare-data-immunity](https://github.com/foolproof-labs/ashare-data-immunity) — data immunity for A-share daily bars

Sister org: [Metabolism Tools](https://github.com/metabolism-tools) — [`workspace-metabolism`](https://github.com/metabolism-tools/workspace-metabolism), policy-driven file lifecycle management for agentic workspaces.

## License

MIT
