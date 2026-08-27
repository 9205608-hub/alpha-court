# RP-1 角色反转外审 —— 两个新 workflow 工位 skill

你是**跨模型对抗外审官**（role-reversal meta-review）。被审对象：两个刚建的"研究流水线工位"skill：
- `.claude/skills/data-pipeline-hygiene/SKILL.md`（工位一：结果存在前的数据入口纪律）
- `.claude/skills/research-session-protocol/SKILL.md`（工位二：一次研究 session 不 p-hack 自己）

你现在就在仓库根（`--cwd`），可用 shell / git / grep **独立核验**任何声称——**只读，不要改文件、不要 commit**。

## 常驻案情（standing case，不可软化）

指挥官（Claude Code）有据可查的毛病，你必须假设它可能又犯了：
- **把 court / quant-mentor / 已有 skill 换皮当"新肌肉"**；v0.1 里程碑 meta-review 打过 **B**；
- 这两个 skill 存在的**全部起因**，就是用户逮到指挥官"把 workflow 描述得跟 court 一模一样、疑似搞混"。
- **已有一轮同模型（Claude）distinctness 门跑过、并砍了它的 flag**——所以你的价值**不是重找那些**，而是
  **独立的跨模型第二只眼：找同模型盲区里漏的换皮 / 事实错 / 宇航味 / 桌面缺口**。

## 任务（REFUTE-first，默认怀疑，逐 skill 做）

1. **仍是换皮吗？** 逐段判：哪句其实是 **court** 干的活（DSR/PBO/BHY/empirical-null，一个你"跑在结果上"的验证器）；
   哪句是 **quant-mentor** 的判断换皮；哪句在复述 **honest-validation**（读判决 + study 级预注册）或
   **factor-research-flow**（机制先行 + net/capacity/orthogonality 三镜头）。读这些的原文对比：
   `.claude/skills/honest-validation/SKILL.md`、`.claude/skills/factor-research-flow/SKILL.md`、`court/`。
2. **L2 绑定 / [LANDED] 声称准不准？** 现读 `adapters/qlib_cn.py` 与 `docs/design/adapter-interface.md`，核对每一处：
   `_build_pit_mask`、`DEFAULT_LABEL_EXPR` = `Ref($close,-2)/Ref($close,-1)-1`、`_shared_kernel` 有限性 +
   `min_cross_section` floor、`data_version` 三元组 + pinned tag、§5.4 declared-not-modeled、§4.4 `COST_DECLARATION`、
   §7.3 `evaluate_shifted` **只 shift score、不 shift label**。有没有对不上 / 夸大 / 张冠李戴。
   baostock 侧字段声称（`pubDate`/`statDate`、`tradestatus`、`isST`、`status`/`outDate`、`adjustflag {1,2,3}`、
   空串→NaN、`SH600000`↔`sh.600000` 代码不一致）是否属实、或有编造。
3. **量化对不对？** K 从 Šidák/BHY 反推的说法；N_eff / garden-of-forking-paths；back-adjust **level** 泄漏而
   **pct-return** 安全；退市终值；成分**公告 vs 生效**滞后；两个 worked 示例的数字是否自洽、有没有误导。
4. **宇航 / 门面 / 心情当阈值** 残留：哪句是招聘噪音、哪个数字无据、哪处把缺口（[DESIGNED]/手动/无成本模型）洗成美德。
5. **两工位彼此边界**干净吗？`adjustflag` 既是 RSP 的 fork、又是 hygiene 的 T5 泄漏——这个分工说清了没、有无矛盾。
6. 一个**资深买方 quant** 读它，会当"能用的工位清单"还是"又一套过程宇航"？每个 skill **最弱一句**是哪句？

## 输出（只输出一个 JSON，可包在 ```json 块里）

```json
{
  "per_skill": [
    {"skill": "data-pipeline-hygiene|research-session-protocol",
     "grade": "A|B|C|D", "verdict": "ship|revise|cannot-ship-as-is",
     "criticisms": [{"claim":"...","location":"§/行","severity":"blocker|major|minor","refutation":"你查到的反证","suggested_fix":"..."}],
     "reskin_or_facade": ["仍是 court/mentor/已有 skill 换皮、或门面/宇航的具体句子"],
     "quant_errors": ["量化或 L2 事实错的具体句子 + 正解"],
     "strongest": "...", "weakest": "..."}
  ],
  "cross_boundary_issue": "两工位边界是否清晰/有无重叠矛盾",
  "verified": ["你实际跑的命令 + 结果，逐条"]
}
```

先通读两个 SKILL.md 全文 + adapter 代码/契约，再动手核验（真的跑命令），最后出 JSON。诚实优先于礼貌——
这两个 skill 的整个立论就是"不是 court 换皮、是能用的研究工位"，你要做的就是替它把这个关。
