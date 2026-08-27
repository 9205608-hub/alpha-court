# 02 工程底座（M0 的最小真实票）

Type: task
Status: resolved
Assignee: dispatched to grok worker via M0 bridge (worker ticket: ../../dispatch/v0.1-02-repo-scaffold/ticket.md)
Blocked by: 01
Label: wayfinder:task

## Question

Python 工程底座落地，同时充当 [01 M0 指挥→工人桥](01-m0-commander-worker-bridge.md) 的全链路验证载荷（本票经桥派给 grok 执行）：

- `pyproject.toml`：包名、Python 版本下限、依赖声明——**`court/` 的运行时依赖白名单 = numpy/pandas/scipy**（qlib 只允许出现在 `adapters/` 的可选依赖组，解耦铁律的工程化表达）
- pytest 骨架：`tests/` 目录 + 一个针对包可导入性的冒烟测试
- ruff 配置（lint + format）
- 各层目录变成真正的包（`court/__init__.py` 等，替换 .gitkeep）

验收：`pip install -e .` 成功；`pytest` 绿；`ruff check` 干净；`court/` 依赖树里 import 不到任何市场特异库。

## Answer

grok 工人交付，referee 独立复核后收货（2026-07-10，commit `e3b5306`）：

- `pyproject.toml`：alpha-court 0.1.0.dev0，setuptools 显式包列表（court/harness/gates/adapters，examples 不入包）；运行时依赖 numpy/pandas/scipy；可选组 `qlib`（只给 adapters 用）、`dev`（pytest/ruff）；ruff（py310, line 100, E/F/I/UP）与 pytest 配置内置。
- 四层目录转正为包，各带一段说层职责的英文 docstring；`examples/` 保持非包。
- `tests/test_smoke.py` 两个测试，其中 `test_court_market_agnostic` 把解耦铁律写成可执行断言：子进程 import court 后断言 qlib 与 adapters 都不在 sys.modules。
- referee 独立重跑：pytest 2 passed、ruff 全净、四包导入 OK——不采信工人 self_test，结论一致。
- 备注：本票经首跑（隔离失效的桥）交付，工人实际跑在指挥 checkout——内容合格照收，过程缺陷记在 [01 M0 指挥→工人桥](01-m0-commander-worker-bridge.md) 的 Answer 里并已修复。
