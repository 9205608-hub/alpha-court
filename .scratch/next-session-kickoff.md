# alpha-court — 下个 session kickoff（v0.2 设计层收官后）

> 用法：新 session 开场把「## 启动 prompt」整段贴进去即可。上半页是本 session 8-commit
> 总账，供你/我快速对齐。

---

## 一页纸总账：本 session 8 commit（分支 `claude/continue-previous-work-6d9434`，领先 `main`=`c7a0d0f`）

**弧线**：v0.1 收尾 → v0.1 里程碑审计修 3 真 bug → v0.2 开图切 12 票 → 四张核心设计 grilling 全定案。全程"与 grok 积极沟通反馈"跨模型互审。

| # | commit | 一句话 |
|---|---|---|
| 1 | `a93b16d` | **双语 README v2**（首屏 hero 图 + 0/100 + size/power 诚实边界）+ 私密上下文 scrub。grok 多轮评审判 Ship；抓到 v1 的 hero 图注张冠李戴等 6 处 |
| 2 | `9cd4a5a` | **v0.1 审计修 3 真 bug**（TDD 红绿，148 passed）：① DSR 反保守 N̂∈(1,1.29) 给近零技能发证 → clamp max_z≥0；② p_from_t 极值下溢→norm.sf；③ DSR 值落盘。① 是 Claude 独立重导抓到、grok 自审漏掉 |
| 3 | `6ef810d` | **v0.2 backlog**：`.scratch/v0.2/` 1 map + 12 票，tracer-bullet + blocking 图 |
| 4 | `03cef8e` | 01 power 标定 v1（grilling-locked 草稿） |
| 5 | `0c5dad4` | **01 power 标定 RESOLVED**：批量 grok 抓出 v1 把主曲线锚到 ICIR 0.1–1.5=画在空集上的锁错 → 校正 A 密在 2.0–5.0。`power-calibration.md` v2、网格冻结 |
| 6 | `3d54300` | **03 选择–判决同构 RESOLVED**：DSR two-sided 弃权（grok 证无干净文献形）+ PBO 换 \|ICIR\|；verdict 加 `role: discriminating/informational`，全票制只计判别关。`selection-verdict-isomorphism.md` |
| 7 | `9a300d1` | **02 预注册闸 RESOLVED**（v0.2 核心）：court 不动 + `harness/` 认证路径 + 哈希链 seal 证书。grok 钉死 tamper-evident（非 proof）/外锚一次于 seal/哈希不覆盖真钟+sort_keys。`prereg-gate.md` v2 |
| 8 | `973fd8d` | **10 dispatch+治理 RESOLVED**：dispatch 泛化=隔离两接缝（非造注册表）；referee 治理=记录 RP-1 绑定接 L1。**v0.2 设计层收官**。`dispatch-and-governance.md` |

**当前状态**：v0.1 完工（0/100 killer demo）；**v0.2 四张设计 grilling（01/02/03/10）全关**，map 进入纯实现阶段。**未合回 main**（8 commit 在分支）。

**v0.2 实现前沿（全 ready-for-agent，除 11 验收）**：05 power 大跑（网格冻，~1.5–2 天）/ 06 ledger 证据层→07 预注册闸本体 / 08 选择–判决对齐（含 killer-demo 真数据重生成）/ 09 聚合上链 / 04 白名单 / 12 nits / 10-refactor。

**已知待处理**：committed `examples/killer_demo/out/ledger.jsonl` 因 DSR 值落盘（commit 2）落后一字段，待真数据重跑重生成（08 处理）。收尾遗留：演示录屏 + GitHub 建仓（`.scratch/` 去留 + CLAUDE.md 已 scrub 求职字样）。

---

## 启动 prompt（贴进新 session）

接续 alpha-court（`一个不会骗自己的挖因子 agent`；单一真相源 `docs/private/00-项目宪章.md`）。上个 session 完成了 v0.1 收尾 + v0.1 里程碑审计（修 3 真 bug）+ v0.2 开图切 12 票 + **四张 v0.2 核心设计 grilling 全部定案（01 power 标定 / 02 预注册闸 / 03 选择–判决同构 / 10 dispatch+治理）**，v0.2 进入纯实现阶段。8 个 commit 在分支 `claude/continue-previous-work-6d9434`（未合 main）。

**这个 session 我要两件事：**

**(1) 先让我获知项目的完全情况。** 请你自己读全下面这些、然后给我一份**项目现状全景**（v0.1 已交付什么、v0.2 设计定了什么、实现前沿、已知债务、离"能上真案"还差什么）：
- `TIMELINE.md` 顶部四条（本 session 全程）
- `.scratch/v0.2/map.md`（v0.2 地图 + 12 票 + blocking）
- 四张 v0.2 设计契约：`docs/design/power-calibration.md`、`docs/design/selection-verdict-isomorphism.md`、`docs/design/prereg-gate.md`、`docs/agents/dispatch-and-governance.md`
- `docs/design/court-kernel-spec.md`（内核 spec，含本 session 的 C4/G5 勘误）、`.scratch/next-session-kickoff.md`（本文件的总账）
- `docs/private/00-项目宪章.md`（定位/受众/路线，私密不外泄）

**(2) 好好用 grok 审计 v0.2 设计层——趁实现还没开始，把设计缺陷抓在 ~1.5–2 天施工之前。** 沿用 v0.1 里程碑审计的方法论（跨模型 + 独立面板 + 对抗，见 `adversarial-referee` 技能 + `.scratch/dispatch/v01-audit/` 先例）：
- **审计对象 = 四张 v0.2 设计契约本身**：每张单独 sound 吗？**四张之间互相一致吗**（尤其 01↔03 的 directional/signed-PBO 分支、02↔03↔09 的聚合上链接缝、02 的 harness 认证路径 vs 03 的 role 机制）？**可实现吗**（06→07→09→08→05 的实现顺序有没有隐藏死锁）？合起来**能不能组成一个自洽的 v0.2**？
- 方法：给 grok 一个 HEAD 只读 worktree + 四张契约全文，让它以"曾经的工人 + v0.1 审计者"身份挑刺；**并行开 Claude 独立面板**交叉检验（grok 审自己参与设计的东西有盲点，v0.1 就是 Claude 独立重导抓到 DSR 反保守）。按 RP-1：这是"里程碑审"触发点，走完把 meta-review 档案 commit 到 `.scratch/dispatch/`。
- 产出：设计层审计报告（哪张契约有洞、哪处跨契约不一致、实现顺序是否安全）→ 据此决定先派哪张实现票。

**工作流规矩**（本项目已固化，见 `docs/agents/dispatch-and-governance.md`）：与 grok 积极沟通反馈、批量过 grok 于契约冻结/里程碑前；referee 双向问责（裁判也会错、独立复核不照单全收）；禁赢学（难看也如实报）。中文沟通、代码/文档英文。

先做 (1) 给我全景，再一起定 (2) 的审计怎么跑。
