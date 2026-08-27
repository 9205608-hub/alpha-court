# 09 聚合口径显式化 + 落盘

Type: task
Status: resolved
Triage: done
Blocked by: 02, 06
Label: wayfinder:task

## Question

审计 v0.2 前瞻债：**聚合口径硬编码在 demo**（全票制一驳即死在 `examples/killer_demo/
aggregate.py`，judge 正确地不做跨统计聚合 `court/judge.py:6-7`）。harness 里若不把聚合
做成**显式配置并落盘**，"一票否决 vs 加权 vs 判别关计票"就会变成**第二研究自由度**
（选一个让被告死/活的聚合规则 = 自欺）。

- 把聚合规则从 demo 提到 harness 的**显式 config**，且**先于判决落盘**（预注册：聚合规则
   不得在看到判决后再选；接 02 的留痕/RP-0）。
- 与 08/03 的"只对判别关计票"口径一致（若 03 走该路径，聚合需感知每关适用性）。
- 落点：`harness/`（config schema + 落盘）；demo 改为引用 harness 的聚合而非自带硬编码。
- TDD 红绿：先写"聚合规则可在判决后被替换而无痕"的失败测试，再堵住。

## 验收标准

- 聚合规则是显式 config、先于判决落盘、事后不可无痕替换。
- killer-demo 走 harness 聚合，头版结论不变（全票制 → 0/100）。
- ruff 净、零回归。

## 审计修订（2026-07-12，v0.2 设计层审计 D15/D16 — 冲突处以本节为准）

- **Blocked by 改为 02, 06**：聚合策略是链上 `declaration` 事件（事件类型由 06 落地），
  "首 verdict 前上链、seal 复核 policy id"（02 v3 §4.2/§7）没有链就没有落点。
  文件级 config（可无痕替换）不满足"事后不可无痕替换"验收，不接受。
- **聚合必须 role 感知**（03 v2 Q3：只计 `discriminating`）——role 字段由 08 落
  `VerdictRecord`；09 与 08 的顺序按 map 冲突矩阵（06 → 08 → 09），09 只改编排引用、
  **不再重生成 demo 产物**（08 已重生成一次）。

## Answer（2026-07-13 收货，referee 终裁）

**已交付并收货，零返工**：dispatch `v0.2-09`（工人 grok，单轮 `ea21442`）。4 文件 +593/-69：
`harness/aggregation_policy.py`（AggregationPolicy frozen dataclass + declare/read/apply +
搬入 08 版聚合五函数）、demo aggregate.py 变 thin delegation（`__all__`、identity 级单一
代码路径）、`aggregate_sweep_rows` 留 demo、harness/__init__ 诚实 docstring + 四导出。
demo 输出字节级冻结兑现（out/ 零 diff）。

**收货强度**：双面板全接受——保真 9 组逐条 ✓（五函数与 08 版逐行语义相等零"改进"）；
探针 49/49 零 fail-open（构造/排序守卫/双 policy/bypass/链交互/sealed 拦截/e2e 全过，
10 个 fixture case 与 HEAD~1 旧实现 oracle 级双向等价）。裁判复跑：20 策略测试 +
46 demo/judge 测试 + ruff 全绿。

**归因入账**：零 worker-fault。唯一 deviation（AC-3 三个 legacy fixture 失败）= **CR-09
复发 #3（contract-fault，指挥官）**——08 重生成把 committed 账本变 chained、没重跑消费
它的测试；工人 stash 级精准归因、referee 亲证后指挥侧修复（合成 legacy 夹具 + 升级版
chained 真产物测试），规则加固进 CR-09。两条 ⚠（链序核对/payload 原文比较）已写入
07 票面交接注记；params 引用存储 nit 入 12。
