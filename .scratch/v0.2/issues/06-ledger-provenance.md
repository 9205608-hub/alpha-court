# 06 ledger provenance：source_ref 可达 + declared↔series 一致性

Type: task
Status: resolved
Triage: done
Blocked by: 02
Label: wayfinder:task

## Question

预注册闸的**证据层**（按 02 拍板落地）。审计 arch 两 major：

1. **source_ref 公共 API 不可达**（`court/ledger.py:430-436` 签名无参、`:455` 硬编码
   `None`；但 `TrialRecord` 字段与 replay `:348` 都支持它）。加 `register()` 的可选
   `source_ref` 参数并串进 trial 事件。
2. **adapter provenance 在 ledger 边界被丢**（`record()` 只收裸序列，`adapters/
   qlib_cn.py:487-506` 的 meta dict 无路进账）。按 02 裁定，让 evaluation 事件携带
   adapter 背书的 protocol 描述符（metric/window/adapter_version/data_version），并在
   `record()` 时与 declared 交叉核对（一致性 fail-closed），或存于 source_ref 之下。

- 纵切：一条"register(带 source_ref) → adapter 评价(带 meta) → record(核对 declared) →
  replay 还原全链"的可复放证据路径。
- 文件边界：`court/ledger.py` + 相关测试（+ adapter 侧最小改动，若 02 决定 adapter 背书）。
- TDD 红绿：先写"source_ref 不可达""declared↔series 不符却静默通过"的失败测试。

## 验收标准

- `register(..., source_ref=...)` 写入并经 replay 还原（round-trip 测试）。
- declared.metric/window 与 record 的 series 不符时按 02 裁定 raise（fail-closed）。
- 现有 ledger 测试零回归；ruff 净。

## 审计修订（2026-07-12，v0.2 设计层审计 D7/D14 — 本节扩充上文范围，冲突处以本节为准）

- **06 是 `court/` 全部改动的唯一属主**，交付清单在原两项之外补三项（02 v3 §3/§7）：
  1. **哈希链字段 + 规范序列化**进 `_append_event`：`content_hash`/`prev_hash`/
     `event_hash` 按 02 v3 §4.1（`type` 入 content、`at` 不入；hash 路径
     `sort_keys=True` + float 先递归替换为 `struct.pack('<d',x).hex()` 再 dumps；
     **存储行序列化一个字节都不动**——12 号票的撕裂恢复语义依赖它）。
  2. 两个 **court-opaque 事件类型**入 ledger 词表：`declaration`（payload 不解释；
     harness 用于 run_config 与 09 的聚合策略）与 `seal`。replay 存取不解释。
  3. 红测：**篡改中段任一行 → replay 校验失败**；追加于 seal 之后 → 校验失败。
- **一致性核对的 declared 侧分家**（02 v3 Q4）：`metric`/`window` 对 `DeclaredProtocol`；
  `universe`/`*_version`/adapter config 对 run 级 **`run_config` declaration 事件**
  （07 的 harness 检查；06 只负责事件类型与链，**不**扩 `DeclaredProtocol`）。
- 验收标准相应追加：链 round-trip（reopen 后 chain head 复算一致）、篡改红测、
  declaration/seal 事件 replay 还原。

## Answer（2026-07-13 收货，referee 终裁）

**已交付并收货**：dispatch `v0.2-06`（工人 grok，两轮：`a6abc9b` 初交 + `5f80ed3` rework-01）。
`court/ledger.py`（+341）+ `tests/test_ledger_chain.py`（+768，31+9 新测试）。四件套全落：
source_ref 打通 / attestation 写时+replay 双检 / 哈希链（含 legacy 同质兼容、seal-final、
诚实边界 honesty test）/ declaration+seal 事件类型。裁判独立复跑：全量 219+1（初交）+
返工后复验、diff 边界干净、对抗探针面板 30+ 探针零 fail-open 零误杀。

**归因入账（逐笔）**：
- **rework-01（major：非 str dict 键在哈希路径不设防——写入成功、重开假阳性
  LedgerCorruptionError；混合键裸 TypeError）**= **contract-fault 为主**（票面自问自答
  bool/float/NaN 值型、对键型缄默）**+ worker-fault 次之**（fail-closed 是票面硬约束）。
  契约保真面板抓获、referee 双变体独立复现、返工后 referee 亲验修复。
- **AC-4 deviation（全仓 ruff exit 1）**= **contract-fault（指挥官）**：referee 审计脚本
  污染 base（30 错全在 `.scratch/dispatch/v02-design-audit/referee-verify*.py`）。工人
  stash 自证归因 100% 属实、诚实 partial。已立案 **CR-09**（`ticket-self-contradiction`
  复发 #2 → 升格规则"lint 必须真跑环境类 AC 于 base"入全局 worker-dispatch skill）；修复 =
  pyproject ruff `extend-exclude = [".scratch"]`。
- 工人申报纪律：满分（无静默偏离，receipt 数字全部与 referee 复跑吻合）。

**在案边界确认（探针面板，非缺陷）**：全链重写 / 降级 legacy 本层不检测（prereg-gate v3
§6 披露边界，防线在 07 的 seal chain_head 复核）；末行缺信封键走 torn-truncate（等价后缀
截尾）；存储 ensure_ascii=True 与哈希路径 False 的不对称有意且正确。

**留给 07 的 seam（指挥侧记账）**：`DeclarationRecord`/`SealRecord` 无 `court/__init__.py`
包级导出（06 所有权边界正确地未碰它）——07 从 `court.ledger` 直接 import，或并 08 的
`__init__` 改动一起补；`canonical_json`/`content_hash`/`link_event_hash` 公开函数由 07
verify 正式认领。
