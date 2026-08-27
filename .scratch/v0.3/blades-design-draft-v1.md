# v0.3 gates/ 刀片库设计草案 v1（2026-08-13 夜，未冻结）

> 宪章 §架构：`gates/ 便宜刀刀片库（v0.3）：恒等式退化检查、池内冗余 ρ、
> 量级 vs 换手、单年运气热力图`。
> 本草案 = 四刀契约 + 共同骨架 + 接缝决策；待跨模型对抗审 + owner 拍板后
> 冻结为 `docs/design/blade-library.md`。

## 0. 立意（为什么是"便宜刀"）

法庭的贵资产是 battery（power 标定过的判决火力，31h 级）。刀片库的存在
理由是**在烧机之前用秒级检查砍掉注定不值得审的候选**，并把"为什么砍"
作为证据入账（null 博物馆的供给侧）。三条设计公理：

- **A1 便宜**：单刀 O(序列长度) 或 O(池大小×长度)，秒级，零拟合。
- **A2 市场无关**：court 铁律不破——刀片只吃 series/标量参数，不 import
  任何市场设施（成本模型、换手口径由 adapter 侧算好传入）。
- **A3 证据先于裁决**：每刀输出完整证据对象；"砍"默认是 informational
  记账而非 discriminating 判死（复用 03 的 role 机制），除非 spec 显式
  把某刀声明为判别关。

## 1. 共同骨架

```python
# court/gates/base.py
@dataclass(frozen=True)
class BladeReport:
    blade: str                 # "identity_degeneracy" | "pool_redundancy" | ...
    flagged: bool              # True = 建议不进 battery
    statistics: dict[str, float]   # 全部数值证据（可复算）
    evidence: dict             # 定位性证据（哪个参照、哪年、哪档成本）
    params: dict               # 本次调用的全部参数（复现用）
```

- 纯函数、无 IO、无随机（需要 bootstrap 的刀显式收 `seed`）。
- 注册进 harness 认证路径时，BladeReport 以 declaration/verdict 事件入
  ledger（哈希链覆盖）；**入账口径是 v0.3 的接缝决策 D1（见 §3）**。

## 2. 四刀契约

### 2.1 identity_degeneracy（恒等式退化检查）

- **问题**：候选"因子"是已知量的平凡变换（参照系的 ±1 倍、lag、rank 单调
  变换），即"重新发明了收盘价"。
- **入参**：候选 series x；参照 series 集 refs（adapter 侧备好：基准收益、
  已知风格因子收益等）；变换族 T = {identity, negate, lag±k (k≤K), rank}；
  阈值 rho_max（默认 0.98？——待标定，见 OQ1）。
- **统计量**：max_{r∈refs, t∈T} |spearman(x, t(r))|；并报次大值防"恰好
  一个参照缺席"。
- **flag 条件**：max ≥ rho_max。
- **证据**：命中的 (ref_id, transform, ρ)、全矩阵 top-5。

### 2.2 pool_redundancy（池内冗余 ρ）

- **问题**：候选与已收录池成员近同——即使真，它不添加正交信息。
- **入参**：候选 x；池成员 series 列表 pool（含各自 id）；ρ 阈值
  rho_pool（默认 0.9？OQ1）；可选：净暴露口径（先不做，v0.3 只做裸 ρ，
  正交化增量留 v0.4，防镀金）。
- **统计量**：max/top-5 |pearson| 与 |spearman|（双报，防非线性单调）。
- **flag 条件**：max ≥ rho_pool。
- **与 2.1 的分界**：参照系=外生已知量（不动的坐标系）；池=法庭自己收录
  的活资产。代码同构但语义与阈值不同，分两刀不合并（null 博物馆归因要
  分得开"平凡退化"vs"池内重复"）。

### 2.3 magnitude_vs_turnover（量级 vs 换手）

- **问题**：毛收益扛不起自身换手的成本地板（证伪总集里"量级扛不起换手"
  的教训模块化）。
- **入参**：毛收益 series r_gross；换手 series（或标量均值）tau；成本网格
  costs（每单位换手的成本，**由 adapter 按市场口径换算好**，court 不知道
  bp 是什么市场的 bp）；显著性参数（NW lag 等，复用 court.tstats）。
- **统计量**：对每档 c ∈ costs：net = r_gross − c·tau；报 net Sharpe（复用
  court.sharpe）+ NW-t；找 break-even c*。
- **flag 条件**：在 spec 声明的"现实成本档" c_ref 下 net-t < t_min
  （t_min 默认 0？1？OQ2——这刀是唯一带显著性色彩的便宜刀，阈值要跟
  02/03 的判决语义划清界限）。
- **证据**：成本-净值曲线表、c*、c_ref 档的 net Sharpe/t。

### 2.4 single_year_luck（单年运气热力图）

- **问题**：裸均值被单块驱动（一致性铁律：判因子看逐块一致性）。
- **入参**：series x + 块标签 blocks（adapter 给定，通常=年，court 不解释
  含义）；bootstrap 参数（B、seed）。
- **统计量**：
  - 分块 Sharpe/均值表（热力图的数据面——court 出矩阵不出图，绘图在
    examples/ 或 adapter 侧）；
  - **leave-one-block-out 最小值**：min_b Sharpe(x \ block_b)；
  - 集中度：HHI(分块贡献) + 置换/块自助 p（单块贡献 ≥ 观测值的概率）。
- **flag 条件**：LOBO 最小值 ≤ 0（去掉最好一块就死）或集中度 p < p_min。
- **证据**：分块表、最坏/最好块 id、LOBO 曲线、p 值。

## 3. 接缝决策（对抗审重点打这里）

- **D1 入账口径**：BladeReport 进 ledger 走什么事件？候选：(a) 新事件类型
  `blade_report`（改 ledger schema，重）；(b) 复用 verdict 事件、
  role=informational、statistic=`blade:<name>`（轻，但 verdict 语义被
  稀释？）。**草案倾向 (b)**——03 已把 role 机制修好，informational 不
  计全票制；null 博物馆按 statistic 前缀溯源。
- **D2 执行位置**：刀片跑在 prereg-gate 之后 battery 之前（spec 冻结时
  声明启用哪些刀+参数——否则"跑了 10 把刀挑 3 把汇报"本身就是自由度）。
  **刀片启用集合与参数必须进 spec 哈希**。
- **D3 flag 的效力**：默认 informational（记账不拦路）还是 fail-closed
  （flag 即不进 battery，除非 spec 显式 override）？**草案倾向：spec 里
  逐刀声明 `on_flag: block|record`，默认 block**——便宜刀存在就是为了拦，
  但拦必留痕（morgue 记 BladeReport 全文）。
- **D4 与 null 博物馆的耦合**：博物馆条目 = morgue 表 + BladeReport 证据
  链，v0.3 item 2 的浏览面直接消费 BladeReport JSON——两票要共享 schema，
  先冻结 BladeReport 再动博物馆。
- **D5 court 依赖面**：全部四刀 numpy/scipy 即可（court-import-gate 白名单
  内）；rank/spearman 用 scipy.stats；不新增依赖。

## 4. 切票草案（收敛后）

- 票 1：`gates/base.py` + identity_degeneracy + pool_redundancy（同构对，
  一票双刀）+ 红先测试。
- 票 2：magnitude_vs_turnover（依赖 tstats/sharpe 复用）。
- 票 3：single_year_luck（bootstrap 帧数最多，单独一票）。
- 票 4：harness 接线（D1-D3 落地）+ spec 哈希扩展 + morgue 记账。
- 票 1-3 文件所有权两两不相交可并行；票 4 串行在后。

## 5. 开放问题（OQ，对抗审请逐条打）

- OQ1：rho_max/rho_pool 阈值怎么定才不是拍脑袋？（候选：用 v0.2 noise
  battery 的纯噪声世界标定假阳率→选阈值使噪声候选 flag 率 ≤ x%）
- OQ2：magnitude_vs_turnover 的 t_min 语义会不会和 battery 判决抢戏？
  （它该是"成本地板粗筛"还是"净显著性预判"？倾向前者：t_min=0 即
  净期望为正即可，把显著性完全留给 battery）
- OQ3：blocks 由 adapter 给定是否破坏"court 不懂日历"？（block 只是
  整数标签，court 不解释——自认合规，请挑战）
- OQ4：四刀都吃"series"，但候选可能有多条 series（IC 与收益）；spec 要
  声明刀吃哪条，还是每刀固定口径？
- OQ5：刀片参数进 spec 哈希后，参数标定实验本身算不算自由度消耗？
  （标定应在 noise 世界做、与真数据隔离——是否需要写进 D2？）
