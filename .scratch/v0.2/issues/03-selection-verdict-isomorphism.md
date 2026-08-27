# 03 选择–判决同构解法设计（HITL grilling）

Type: grilling
Status: resolved
Triage: ready-for-human
Label: wayfinder:grilling

## Question

v0.1 审计判定：**五道关实际只靠一道**（pool-max）；DSR 与 PBO 在 killer-demo 里是
"空转关"，却仍参与"全票制幸存"叙事。根因是**扫描规则与统计原假设不同构**：

- 裸选择 = 全窗 **max|t| two-sided**（允许翻号）。
- **DSR 单侧**：被告翻号反向（t<0，`report.md:16` sr_selected=−0.12）→ DSR 近乎自动
   驳回，deflation 机器几乎没干活；且 ρ̂ 病态是 M=100 常态（T=480<½·100·99），N̂≈N，
   相关性校正空转。
- **PBO 内部有符号 argmax**（sharpe），裸选按 |t|——同一"被告"未必是 PBO 的 IS 最优，
   φ=0.47≈0.5 只说明"噪声矩阵过拟合概率≈抛硬币"，对 |t| 选择的因果指控更弱。

本票拍板解法（禁赢学：地基可以有弱关，但**不能让弱关参与"全票制"叙事却不改协议**）：

1. **对齐扫描规则与统计侧**：让裸选择的规则 ≡ 各关的原假设（如统一 signed、或统一
   two-sided，代价是改 demo 叙事）？还是
2. **按适用性启用**：DSR 仅在**预注册 directional（如 long-only）假设**下启用，不再假装
   五关等价；PBO 的 selection metric 与裸选口径对齐或显式申报差异？还是
3. **逐关申报适用性**：battery 报告里每关标"本案是否是判别性的"，聚合只对判别关计票？
4. **与 02 交叉**：direction 锁定属"闸侧"（02），本票定"统计侧"——两票的裁定不得打架。
5. **spec 落地**：结论要回写 `docs/design/court-kernel-spec.md`（判决极性表/battery
   配置）与 `killer-demo.md`（若改 demo 口径）。

## 产出

设计裁定（`docs/design/` 内新增或改现有 spec/killer-demo）+ spec 勘误行。08 实现票必引。

## Answer

**Resolved 2026-07-11.** grilling（Q1–Q3）+ 一次 grok Q2 咨询（`.scratch/dispatch/v02-03-grill/`，
亲证 PBO-|metric| 站得住、two-sided DSR 无干净文献形）。设计裁定 =
`docs/design/selection-verdict-isomorphism.md`（v1）。

- **Q1 = B**：把 spec F2 的方向感知原则推广到 DSR/PBO——每关跑 declared-direction 一致形；
  有便宜且站得住的一致形就用（保判别），没有就弃权（informational：仍算仍报，不进 survivor 投票）。
- **Q2**：**DSR** two-sided 下弃权（无干净文献 two-sided DSR——N→2N 错、翻号喂原版反保守、
  PSR 偏度修正符号不对称，硬造污染 DSR 名违反引用铁律）；directional 下启用原版有符号 DSR。
  **PBO** two-sided 下换 **|ICIR|/|sharpe|**（CSCV 对度量 agnostic，匹配 max|t| 选择、零分布推导），
  directional 下用有符号。
- **Q3**：verdict 加 `role: discriminating | informational`（判决时派生）；全票制只计 discriminating 关。
  killer-demo（two-sided）判别关 = FDR + PBO(|ICIR|) + pool-max + individual（4 关），DSR informational；
  **头版 0/100 不变**，§6 聚合 + §7.2 叙事作废重写。
- **落地裁定（grok trap A–H）**：metric 注册表方向感知 + params 记实际 R 名（G5 amend）；PBO 一致性
  断言改过程级措辞；φ=0.2 不动；DSR ρ̂ 病态老病弃权不解决（脚注）；IC-发现 vs PnL-优选经济边界 =
  02/03 接缝（03 不写死"永远 |metric|"）。
- **跨票 amendment 已落**：`power-calibration.md` §9（01：power directional 下 DSR 启用 + PBO 有符号，
  运行时按 declared.direction 分支）；`court-kernel-spec.md` G5 后加适用性勘误行；`killer-demo.md` §6 加
  v0.2 revision 注。

**实现归 08 号票**（含 killer-demo 真数据重生成）。**关票。**
