# lesson-book

![PyPI version](https://img.shields.io/pypi/v/lesson-book.svg)
![PyPI downloads](https://img.shields.io/pypi/dm/lesson-book.svg)
![CI](https://github.com/holdout-labs/lesson-book/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

## 中文说明

`lesson-book` 是本地优先、可复现的交易经验记录工具，也可以用于 A 股研究
和模拟交易流程。它记录错误、代价和标签，并在相似情境再次出现时给出提醒。
匹配规则是固定的，不调用大模型、不上传云端，也不提供买卖建议；它的作用是
让过去的经验在行动前被看见。

**交易者的学费记忆（Tuition memory）。** 一个本地优先、确定性的错误账本：
记录每个错误让你付出的代价，给它打上标签，当同样的情境再次出现时，`lb match`
会在你行动**之前**提醒你。要求 Python 3.11+，**零依赖**，支持 Windows / Linux / macOS。
无需 LLM、无需云端、无需统计：提醒可复现、可审计。

**状态（Status）：** v0.1.1 alpha，已发布到 PyPI。匹配逻辑提炼自生产交易系统的
教训匹配模块；这个独立的软件包是全新的。

## 为什么存在

你的交易系统有一个记忆问题：它会遗忘。上个月让你付出 1,200 代价的错误，今天
看起来像是一个全新的机会，因为在想法和下单之间没有任何东西把关。交易日志解决了
*记录* 这一半——它们只是发生过什么的流水账。`lesson-book` 解决的是 *检索*
这一半：它把学费保存在一种形式里，当同样的情境再次出现时，它能够开口提醒你。

两个设计承诺使它区别于日志类应用和 LLM「记忆」系统：

1. **确定性，而非统计性。** 打分是一套固定的加权公式（同代码 +3、同行业 +2、
   同市值 +1、波动率接近度加分、标签重叠加分）。同样的情境，每次得到同样的提醒
   ——与即兴发挥的 LLM 记忆正好相反。
2. **本地优先且可验证。** 账本就是仓库里的一个纯追加（append-only）JSONL 文件。
   对它执行 `git log` 就是你的审计轨迹；没有任何数据离开你的机器。

## 设计哲学

**学费就是资本——系统不会忘记你付出过代价的教训，并会在你再次付出代价之前提醒你。**

这是航空和医学领域的清单文化在交易上的应用：Gawande 的
[*《清单革命》*](https://en.wikipedia.org/wiki/The_Checklist_Manifesto)
是「简单的清单能把灾难性错误率降低一个数量级」这一论点的经典论证。它同时也是
反向的**事前验尸（premortem）**：
[Klein (2007)，「Performing a Project Premortem」](https://hbr.org/2007/09/performing-a-project-premortem)
要求你在行动之前，先想象自己已经失败了，并解释为什么会失败。`lb match` 就是
自动化的 premortem：它把「这为什么会失败」的历史答案呈现出来，无需你亲自发问。

[IOM (1999)，*To Err Is Human*](https://nap.nationalacademies.org/catalog/9728/to-err-is-human-building-a-safer-health-system)
（《人非圣贤，孰能无过》）的框架直接适用：错误是系统问题，而不是人品缺陷。
账本的存在是为了改进系统——分类、复盘与检索——绝不是为了惩罚个人。正因为如此，
记录带有 `cost`（一个数字，而不是一种羞耻），也正因为如此，工具只做分类而从不
强制执行：规则、仓位和限制仍由你掌控。

## 快速开始

```bash
# install the published package from PyPI
pip install lesson-book

# or run without installing anything:
#   PYTHONPATH=src python -m lesson_book --help

python examples/demo.py   # record, match, review on a scratch book
```

创建你自己的账本：

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

## 命令

| 命令 | 作用 |
| --- | --- |
| `add` | 记录一个错误：`--title`、`--issue`（必填）、`--error-category`、情境字段（`--code`、`--industry`、`--volatility`、`--market-cap`、`--tags`）、`--cost`、`--lesson`、`--situation`。通过规则表分类（P1/P2，无法分类时默认归为 P2） |
| `import-lessons` | 将带 `**Field:**` 元数据（Code/Industry/Volatility/Market Cap/Tags/Cost/Lesson/...）的 `##` 标题式 Markdown 知识库解析进账本。按标题幂等 |
| `match` | 对与当前情境相关的教训排序；没有匹配时以退出码 1 结束（行动前的钩子可以据此 fail-closed——没有匹配时默认不放行） |
| `review` | 每日复盘：按类别和优先级分组的卡片、总代价、Markdown 输出 |
| `version` | 打印版本号 |

## 账本（the book）

`book.jsonl` —只追加（append-only），每行一条 JSON 记录：

```json
{"schema_version": "lesson_book.lesson.v1", "record_id": "...",
 "title": "bought into the open gap", "date": "2026-08-01",
 "code": "600000", "industry": "banking", "volatility": 0.03,
 "market_cap": "large", "tags": ["gap", "limit-up"],
 "category": "price_limit_rejected", "priority": "P1",
 "cost": 1200.0, "lesson": "never chase the open gap",
 "situation": "", "recorded_at": "..."}
```

匹配得分（确定性公式）：

| 信号 | 权重 |
| --- | --- |
| 相同代码 | +3.0 |
| 相同行业 | +2.0 |
| 相同市值 | +1.0 |
| 波动率接近 | 最高 +1.5（按差距的 5 倍衰减） |
| 标签重叠 | 每个标签 +0.5，上限 +1.5 |

主匹配（代码 / 行业 / 市值）是得分非零的必要条件——对于没有依据可比较的情境，
账本绝不会开口。

## 分类规则

`add` 通过一张普通规则表（`category`、`priority`、`action`）对
`issue` + `error_category` 进行分类，可在代码中完全覆盖。默认规则：

| issue | error_category | category | priority |
| --- | --- | --- | --- |
| `execution_without_action_plan` | —| `planning_gap` | P1 |
| `execution_failed` | `price_limit` | `price_limit_rejected` | P1 |
| `execution_failed` | `trading_time_closed` | `trading_time_closed` | P1 |
| `execution_failed` | `receipt_reader_error` | `receipt_reader_error` | P1 |
| `execution_failed` | —| `execution_failure` | P1 |
| 其他任何情况 | —| `unclassified` | P2 |

未分类的记录归为 P2，并标注「请人工复核并扩展规则表」——分类体系随你一起成长，
绝不会悄无声息。

## 开发

```bash
python -m pip install -e . pytest
python -m pytest
```

CI 在 Ubuntu、Windows 和 macOS 上以 Python 3.11 和 3.12 运行完整测试套件。
问题（issue）在周末处理；欢迎提交 pull request。

## 相关工作

- [Klein (2007)，Performing a Project Premortem（HBR）](https://hbr.org/2007/09/performing-a-project-premortem) —在失败发生之前先想象失败
- [Gawande (2009)，The Checklist Manifesto（《清单革命》）](https://en.wikipedia.org/wiki/The_Checklist_Manifesto) —把清单作为降低错误率的手段
- [IOM (1999)，To Err Is Human](https://nap.nationalacademies.org/catalog/9728/to-err-is-human-building-a-safer-health-system) —把错误视为系统问题

## 项目家族

属于 [Holdout](https://github.com/holdout-labs) ——一个对抗量化研究中的自我欺骗
的工具链：

- [pit-adjuster](https://github.com/holdout-labs/pit-adjuster) — PIT 后向复权，带静态前向复权漂移检测
- [falsification-ledger](https://github.com/holdout-labs/falsification-ledger) — 预注册与证伪账本
- [factor-qc](https://github.com/holdout-labs/factor-qc) — fail-closed（无匹配即拒绝）的回测质量闸门
- [lesson-book](https://github.com/holdout-labs/lesson-book) — 交易者的学费记忆
- [lookahead-free](https://github.com/holdout-labs/lookahead-free) — 可验证的无前视偏差（look-ahead）检查
- [ashare-data-immunity](https://github.com/holdout-labs/ashare-data-immunity) — A 股日线数据免疫

姊妹组织：[Metabolism Tools](https://github.com/metabolism-tools) —
[`workspace-metabolism`](https://github.com/metabolism-tools/workspace-metabolism)，
面向 agentic（智能体式）工作区的策略驱动文件生命周期管理。

## 许可证

MIT
