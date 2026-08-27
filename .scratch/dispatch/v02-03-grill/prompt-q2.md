# 咨询：选择–判决同构（ticket 03）的 Q2 —— DSR/PBO 的适用性处理

你是 grok-4.5，alpha-court 主力工人（court 内核大多你写的）。指挥官与用户在 grill
ticket 03（`.scratch/v0.2/issues/03-...md`）：v0.1 审计判定"五关实际只靠一关（pool-max），
DSR/PBO 是空转关却仍进全票制"，根因是**扫描规则与统计原假设不同构**。给真专家意见，
别附和。你的 cwd 是只读检出，可读 `docs/design/killer-demo.md`（§5 两臂、§5.4 subtlety）、
`docs/design/court-kernel-spec.md`（F2/G2/G5、DSR/PBO 极性）、`docs/research/{dsr,pbo-cscv}.md`。
不要改文件，输出文本。

## 已锁定（Q1，勿推翻）

裸选择 = `max|t|` 允许翻号、declared `direction="two-sided"`（有效 200 臂 = 2N 单侧）。
FDR（two-sided p）、pool-max（`abs_t_iid`）、individual（|t|）**已与 two-sided 一致**。
只有 **DSR（有符号单侧）** 与 **PBO（每组合有符号 argmax，metric=sharpe/ICIR）** 不同构。
**Q1 裁定 = B**：把 spec F2 的原则（"噪声关按 declared.direction 取有向统计量、court 从不
自己推方向"）推广到 DSR/PBO——**每关跑 declared-direction 一致的那一形；有便宜且站得住的
一致形就用（保持判别）；没有就弃权（informational，仍计算+报告，但不进"全票制"投票）**。

## Q2：DSR 与 PBO 各自怎么处理？

指挥官推荐：
- **DSR**：two-sided 下**弃权**（理由：two-sided DSR = 削 |SR| 对 2N 臂的 E[max|SR|]，是需
  文献推导、可能站不稳的扩展；Bailey-LdP 原版单侧）。directional 下适用（正是 v0.2 power
  实验的 β>0 场，DSR 在那才真判别）。
- **PBO**：two-sided 下把内部 IS argmax 从**有符号 sharpe** 换成 **|sharpe|（|ICIR|）**，匹配
  `max|t|∝max|ICIR|` 的选择——**无需分布推导**（judge 本就按 direction 接 metric callable），
  保持判别。directional 下用有符号。

**替代**：DSR 和 PBO **都弃权**（更简单统一，但浪费 PBO 那关）。

## 请你回答

1. **PBO-by-|metric|（|ICIR|）在 two-sided |t| 选择下是站得住的 CSCV 变体吗？** 换 |·| 排序
   会不会破坏 CSCV 的对称性/OOS 秩语义、或引入新偏？还是它恰恰是"|表现|选择"的正确过拟合量？
2. **two-sided DSR 真的没有干净的文献形吗？** 削 |SR| 对 2N 臂 max|SR| 的 deflation——Bailey-LdP
   或后续文献里有没有站得住的版本？指挥官"弃权而非硬造"对，还是漏了一个该用的？
3. **裁定 Q2**：DSR 弃权 + PBO 换 |metric| / 两关都弃权 / 别的？一句话理由。
4. 有没有指挥官没看见的陷阱（比如：PBO 换 metric 后与 killer-demo 的 pool-max 一致性断言、
   或与 power 实验 directional 场的 PBO 口径不一致）？

中文纯文本，诚实刻薄优先。
