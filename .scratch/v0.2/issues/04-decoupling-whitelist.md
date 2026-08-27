# 04 解耦守卫升级：test_smoke 黑名单 → 白名单

Type: task
Status: resolved (2026-07-31, adjudicated without dispatch — see Answer)
Triage: ready-for-agent
Label: wayfinder:task

## Question

铁律一（`court/` 零市场特异 import）的**可执行守卫弱于铁律本身**。审计 arch major：
`tests/test_smoke.py:28-35` 的子进程断言只检查**没有 `qlib*` / `adapters*`** 泄漏进
`sys.modules`（二名黑名单）——court 若误 `import tushare`/`akshare`/`baostock` 或任何
其它市场库，此测**照样过**。spec §3.1 要求 court 只依赖标准库 + numpy/scipy(+pandas)。

**任务**（TDD 红绿，独立小改，不阻塞任何票，可当 v0.2 首个早绿）：

- 把断言改成**正向白名单**：`import court` 后，子进程 `sys.modules` 里每个**新增的顶层
  模块**必须 ∈ {标准库} ∪ {numpy, scipy}（core 当前不用 pandas——确认后决定是否纳入）。
- 先写 RED：构造一个"court 顶层引入了一个白名单外模块"的失败断言（或用 monkeypatch/
  子进程注入证明黑名单会漏、白名单会抓），再改实现转绿。
- 保留原黑名单断言作为额外冗余无妨；核心是白名单成为主守卫。
- 文件边界：仅 `tests/test_smoke.py`（如需小工具函数就地写）。

## 验收标准（referee 可独立复跑）

- `python -m pytest tests/test_smoke.py -q` 全绿。
- 反证：临时在 `court/__init__.py` 顶部加一个**白名单外的第三方顶层 import**（如
  `import pytest` 或任一市场库，凡不属 {标准库, numpy, scipy} 者），白名单断言必须
  **FAIL**（证明守卫真的抓得住），复原后转绿。注意标准库模块（json/http 等）属白名单、
  不能用作反证。
- ruff 净。

## Answer（2026-07-31 指挥官/referee 裁定：不派单关票）

**裁定：issue 的实质已由后落地的 `harness/court_import_gate.py` 以更强形式满足；
issue 开出的具体处方经实证不可实现。本票不再派工，凭下列可复跑证据关闭。**

### 1. 处方不可实现（派单前对抗 lint 亲跑 AC 逮到）

票面处方"`import court` 后新增顶层模块 ∈ {标准库} ∪ {numpy, scipy} 名字白名单"在
基座 `52566a27` 真机上**天然红**，8 个白名单外顶层模块全部来自被允许的科学栈自身：

- `_csparsetools` / `_cyutility` / `_moduleTNC` / `_ni_label` — scipy 编译扩展，
  文件在 `site-packages/scipy/**` 内，但以顶层名注册进 `sys.modules`；
- `_cython_3_2_4` / `cython_runtime` — cython 运行时伪模块（无 `__file__`，
  前者名字嵌 cython 版本号——名字白名单天生脆的铁证）；
- `_sysconfigdata__darwin_darwin` — 平台生成的标准库模块，不在
  `sys.stdlib_module_names`；
- `charset_normalizer` — `numpy/f2py/crackfortran.py:150` 主动 import（import-spy
  栈回溯实证），numpy 自身的传递依赖。

运行时对"传递闭包"做名字白名单 = 误报机器。铁律的真实形状是"**court 自己的代码**
只许 import {标准库, numpy, scipy}"——这正是 AST 门实现的语义。

### 2. 实质已满足（映射到本票原验收标准）

- **白名单成为主守卫** → `harness/court_import_gate.py`：allowlist = stdlib ∪
  {`__future__`, court, numpy, scipy}；覆盖相对 import 逃逸、动态 import
  （含 rebind 链）、exec/eval/compile、按路径加载器、符号链接；解析失败 fail-closed。
  pre-commit 已挂载；且 `tests/test_court_import_gate.py::
  test_clean_court_tree_has_zero_violations` 把门跑在真 court/ 树上，**pytest 套件
  内每次全量都在执行白名单**（不依赖 hook 安装与否）。
- **反证 AC（2026-07-31 亲跑，基座 52566a27）**：`court/__init__.py` 的
  `__future__` 行后注入 `import pytest` →
  门 CLI FAIL exit 1，精确报 `court/__init__.py:9: forbidden import 'pytest'`；
  真树 pytest 测试 FAIL；**旧黑名单 smoke 对同一注入依然全绿**（本票抱怨的盲区
  当场演示，且已被门覆盖）。复原后门 PASS、58 测全绿。
  附带收获：误把注入放 `__future__` 之前（语法错误）→ 门同样 exit 1 fail-closed。
- **保留旧黑名单作冗余** → 原样保留（票面本就允许）。

### 3. 残差与豁免

运行时侧理论残差 = import-spy（逐 import 语句归因发起方是否 court.*），其边际
捕获仅剩"import 时刻 exec 字符串 import"等病态自伤场景——门的 docstring 已把这些
列为 DECLARED LIMITS。裁定为镀金，豁免不建，记录在此。

### 归因

无派单发生。票面处方缺陷由派单前对抗 lint（规则 3：AC 命令必须在基座亲跑）拦截，
未流入工人环——lint 机制按设计生效，不记 fault。未派出的票面留档
`.scratch/dispatch/v0.2-04-decoupling-whitelist/`（标 NOT-DISPATCHED）。
