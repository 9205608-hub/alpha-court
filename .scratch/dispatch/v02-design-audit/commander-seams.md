# 指挥官独立审查记录 — v0.2 设计层审计（第三路）

写于 2026-07-12，**在 grok 盲审与三路 Claude 面板任何输出返回之前 commit**（RP-0：
时间戳证明本路独立）。这些是通读四张契约 + spec + map 时看到的候选疑点，**不是结论**——
待四路对表后逐条裁决（命中/误报/部分命中），裁决入 verdict.md。

面板与 grok 均未被喂入本清单（盲审，用户拍板）。

---

## S1 — prereg-gate 内部：外锚时序疑似自相矛盾

**现象**：
- §4.3（L96–98）：外锚"pinned **once, at seal** — never per-trial"，即锚定发生在
  全部 series 之后。
- §5 fail-closed 清单（L117–118）："a broken hash-chain, or (when an anchor is
  required) **an anchor that does not predate the series** → seal invalid"。
- §7（L160–162）：RP-0 先例 = "results not before the pre-registration commit"
  ——这个先例锚的是**声明先于结果**，与 §4.3 的"锚在 seal（结果之后）"方向相反。

**为什么可能是洞**：按字面，锚若钉在 seal 时刻则永远不早于 series，§5 那条使**每个
带锚的 seal 都无效**；若 §5 是对的，则 §4.3 的"一次于 seal"设计根本提供不了
"declared 先于 series"的外部证明（那本来就靠链内行序）。两条至少有一条措辞错，
或"anchor"在两处指不同对象而契约没区分。

**不改的后果**：07 施工时工人无从实现 anchor 验证逻辑，要么实现一个恒失败的检查，
要么擅自选一种语义（契约漂移）。

## S2 — prereg-gate ↔ spec schema：attestation 检查的 declared 一侧缺字段

**现象**：
- prereg-gate Q4（L30）与 §5（L109–111）：harness 检查 attested == declared，字段
  含 metric / window / **universe** / *_version / n_evaluation_dates。
- spec §5.7 `DeclaredProtocol`（L391–396）字段 = metric / window / periods_per_year /
  direction / se——**没有 universe**，也没有版本类字段。
- prereg-gate §3（L35–37）声称 court 侧只改"ticket 06 的 source_ref 可达 + 可选
  `record(..., attestation)` 参数"。

**为什么可能是洞**：`attested.universe == declared.universe` 的右边不存在。要么 06
必须扩 `DeclaredProtocol` schema（超出 §3 的"court 不动"声称范围），要么 universe
落在 opaque 的 spec/params dict 里（那"机械等式检查"就检查不了 typed 字段，契约
没写这条路），要么 attestation 清单该缩水。三选一没定。

**不改的后果**：06/07 两票各自猜一种，缝在集成时才炸；或 conformance 检查静默少查
universe——恰是"缩 scope 自欺"家族的邻居。

## S3 — 01 ↔ 03：power 实验"选择两侧、判决单侧"，疑似违反 03 自己立的同构原则

**现象**：
- 01 §5（L146–149）："won" = argmax **|t|** 且 raw t > 0（两侧搜索 + flip guard；
  与 size demo 镜像）。
- 01 §9（L222–231）+ 03 §6（L133–138）：power run declares **greater** → DSR 启用、
  PBO 用有符号 metric——battery 是单侧形态。
- spec F2：噪声闸用 declared 方向的定向统计量（greater → t，非 |t|）。
- 03 §1 的立论恰恰是：battery 必须与**选择规则**同构（"裸选 max|t| 是两侧搜索"）。

**为什么可能是洞**：power 的裸选择仍是 200 臂两侧搜索（这是"镜像 size demo"的代价），
但整个 run 按 greater 判——按 03 自己的原则，两侧选择应配两侧 battery（DSR 弃权、
PBO |ICIR|）。两个子问题：
1. 99 个噪声 trial 的 declared.direction 是什么？全 greater（则 FDR 单侧 p、pool-max
   陪审统计量 = t 而非 |t|，多重性口径与两侧搜索的 200 臂不齐）还是混合（契约没写）？
2. β=0 size 锚在 greater battery 下的 unanimous **含 DSR**（directional 下
   discriminating），与 killer demo 的 unanimous（DSR informational、PBO |ICIR|）
   **不是同一台机器**——01 §3 Q3"exact size mirror"与 §6"at β=0 assert
   P(pass) ≈ nominal α"的可比性声称存疑。
（缓解注记：在"won ∧ t>0"分支内，argmax t = argmax |t| 可证一致，所以 pool-max 的
observed 在条件事件内不歧义；问题在 null 分布口径、FDR 家族方向、与 size 锚可比性。）

**不改的后果**：05 跑 ~1.5–2 天出的主曲线，其 β=0 锚与 killer demo 的 0/100 不可比
（README/case-study 若并排引用即自打脸）；或审稿人一眼指出"你们用 03 的原则起诉了
自己的 power 实验"。

## S4 — 05 的 Blocked-by 清单疑似不完整 / 认证路径归属没写死

**现象**：
- map（L77 表 + L93）：05 Blocked by **01, 03**（03 是设计票，实施在 08）。
- 03 §2/§7：role 字段、informational 不入票、direction-aware PBO metric registry
  ——都由 **08** 实现（judge 改动）。
- 01 §6：分闸 TPR 是默认输出；unanimous 的定义 = "all discriminating gates"。
- 02/07：认证路径（propose→…→seal）是 harness 的正门；01/05 只字未提 power harness
  走不走认证路径（power 是构造信号标定，走直调 court 的"未认证计算器"用法本也合法）。

**为什么可能是洞**：
1. 若 05 在 08 之前跑：verdict 无 role 字段，"unanimous 只计 discriminating"得由
   power harness 自行硬编码（与 08 之后的 judge 语义两套实现）；power 产物的 ledger
   schema 与 08 重生成后的 demo 产物不同代（engine_version / 字段集），11 终验对
   两套产物的一致性口径没定。
2. directional 下"全部闸 discriminating"恰好使 unanimous 数值上等于 v0.1 全票制
   ——数值巧合掩盖实现缺位，直到有人跑 two-sided 场景才炸。
3. 05 票面需要显式写"不走 06/07 认证路径（未认证计算器用法，理由：标定实验非
   自欺场景）"或"走"，二选一现在没写死。

**不改的后果**：05 大跑（~1.5–2 天机时）可能要重跑一次（正是 §12/Option 1 想避免的
事，只是这次绕过 03 从 08 咬回来）；或 11 终验时两套产物口径打架。

---

对表规矩：四路（grok / Panel A 统计 / Panel B 机制 / Panel C 一致性）+ 本清单，
逐条裁决入 `verdict.md`；任何一路的批评不得静默丢弃；归因三分（design-fault /
audit-false-alarm / 措辞歧义）逐条入账。
