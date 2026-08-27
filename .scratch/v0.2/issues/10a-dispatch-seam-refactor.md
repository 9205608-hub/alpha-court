# 10a dispatch 两接缝重构 + receipt 验证

Type: task
Status: resolved
Triage: done
Blocked by: —
Label: wayfinder:task

## Question

按 `docs/agents/dispatch-and-governance.md`（含 2026-07-12 审计修订）落地 Part A：

1. `scripts/dispatch.sh` 的两处 grok 特异接缝隔离成 `worker_invoke(ticket, cwd,
   schema, opts) → raw_envelope` 与 `worker_extract_receipt(raw_envelope) →
   receipt_json` 两个函数；隔离/tripwire/schema 其余逐字节不动。
2. **commander 侧 receipt 验证**（审计 major-5）：`worker_extract_receipt` 之后对
   `scripts/receipt.schema.json` 做 jsonschema 校验，失败 = 拒收 exit 非零——不依赖
   任何 worker 的原生 schema 支持。
3. `worker-bridge.md` 补 "Worker generalization" 一节（契约四条 (a)–(d)，含 (d) 全无头）。

## 验收标准

- 现有 grok 派单路径行为逐字节不变（对拍一次真实派单的 receipt/收据路径）。
- 手工喂一个 schema 不合规 envelope → 拒收、exit 非零（红测）。
- shellcheck 净；tripwire 红测（脏树 exit 1）不回归。

## Answer（2026-07-17 收货，referee 终裁 — 零工人返工）

**已交付并收货**：dispatch `v0.2-10a`（工人 grok，单轮 `2b5dae0`）。`scripts/dispatch.sh`
两接缝隔离成 `worker_invoke`/`worker_extract_receipt` + 新 `scripts/dispatch_receipt.py`
（stdlib 提取+校验）+ `worker-bridge.md` Worker-generalization 节 + 11 测试。

**收货强度**：fidelity 面板逐行核 dispatch.sh diff **行为保持**（运行时验证 fake-grok argv 顺序、
`set +e` 守卫捕获非零退出、extractor 失败经 set -e 传播）+ 校验器无漏（我 7 条对抗 + 面板
`pattern` 未实现构造探针 → 正确 raise 非静默过）+ 全 7 AC 兑现。dependency-free 真跑系统
python3 证实。

**归因**：**零 worker-fault**。唯一 AC-4 miss（全量套件 2 个 court_import_gate staged 失败）=
**CR-09 复发 #4（contract-fault，指挥官）**：AC-4 写 `python3 -m pytest`（系统 python3），
在 base 不可满足——07/09 让 `harness/__init__` **eagerly import court.judge**，court_import_gate
staged 测试的子进程 cwd 遮蔽真 court/、系统 python3 把 cwd 上 sys.path → ModuleNotFoundError；
`.venv-merged` 恰好躲过。工人诚实 `partial` + deviation 100% 属实（referee 亲证：base、系统
python3、gate-alone 复现，零工人改动）。referee 修 base（`-P` isolate，56 passed）+ CR-09 规则
加固 (c)「env-AC 用 AC 点名的确切解释器+深度」。1 nit（receipt 尾换行，无害）归 12。
