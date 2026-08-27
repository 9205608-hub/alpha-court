# RP-1 角色反转外审 —— backtest-reuse-guard（工位三）+ 一个 cut 判断复核

你是**跨模型对抗外审官**。被审对象：`.claude/skills/backtest-reuse-guard/SKILL.md`（工位三：回测复用护栏 / anti-NIH 站）。
你在仓库根（`--cwd`），可用 shell / git / grep / python **独立核验**——**只读，不改文件、不 commit**。

## 常驻案情（不可软化）
指挥官（Claude Code）有据可查的毛病：**把 court / quant-mentor / vectorbt-expert / 已有 skill 换皮当"新肌肉"**；上一轮你（grok）给 research-session-protocol 打了 **C**，因为**它教"别拍脑袋"、自己却把 worked 例的 K 数学写错了**。这个 skill 又是一个"复用被审 API、别手搓"的 skill——**同一类翻车最可能重演**。已过一轮同模型 distinctness+correctness 门（判 build/distinct，并修了一处 court API 调错）——你是**独立跨模型第二只眼**：找门漏的。

## 任务（REFUTE-first，逐项）
1. **court API 调用现在对不对？**（上一版把 `Application` 当 kwargs 调错了，已改）——现读 `court/judge.py`、`court/__init__.py` 核对：
   §worked-example 里 `court.judge(ledger, scope, [Application("dsr",{...}), Application("pbo_cscv",{...}), Application("fdr_by",{...}), Application("noise_control",{...})])` 是否与真实签名一致（`Application` 是不是 `NamedTuple(statistic:str, params:dict)` 位置构造；`judge()` 第三参是不是 applications 序列；empirical-null 的 statistic 名是不是 `"noise_control"`）。**能跑就跑一下**验证。
2. **§2 "别重造这些" register 的每个函数/模块名**（`court.sharpe`/`court.dsr`/`court.pbo`/`court.fdr`/`court.noise`/`court.tstats`、`sr_standard_error`、`fdr_by`、`empirical_null_p`、adapter `evaluate`/`DEFAULT_LABEL_EXPR`/`_build_pit_mask`）是否真存在、归属对不对、有无编造或张冠李戴。
3. **解耦法（§3）**是否属实：`court/` 不得 import 市场码；adapter 被契约禁止调 qlib 回测栈（`adapter-interface.md` §4.5）；有没有 [LANDED] 的 decoupling 冒烟测试（`tests/` 里）——现读核对。
4. **仍是换皮吗？** 哪句其实是 court-wiring（court 内部零件索引）、哪句是 vectorbt-expert / quant-analyst 换皮、哪句在复述另外三个工位 skill。`§2` register 是不是 ~85% court-API 索引、"不碰 court 也有用"这条其实只靠 §1 判据 + §4 论点撑着？
5. **宇航 / 门面 / 心情当阈值** 残留；最弱一句。
6. **一个 cut 判断复核**：我把候选 skill `research-brief`（碰数据前一页研究 brief）判为 **cut-as-reskin 砍掉了**——理由：§1=honest-validation§1+RSP§3、§2=RSP kill-test 换粒度、§3=quant-mentor#12+FRF§3 换标签、§4=重复全 workflow 都教的"court 看不见 net-of-cost"；唯一独立点=一个"决策类型→该用什么 metric"的 pre-idea 选择器，但它 discharge 不了任何已命名缺口。**你同意砍吗，还是那个 pre-idea 选择器有值得单独救回的东西？** 别给面子。

## 输出（只输出一个 JSON）
```json
{
  "grade": "A|B|C|D", "verdict": "ship|revise|cannot-ship-as-is",
  "criticisms": [{"claim":"...","location":"§/行","severity":"blocker|major|minor","refutation":"查到的反证","suggested_fix":"..."}],
  "api_l2_correctness": ["每处 court/adapter API 声称的核验结论：对/错+正解"],
  "reskin_or_facade": ["仍是换皮/门面/宇航的具体句子"],
  "strongest": "...", "weakest": "...",
  "research_brief_cut": "agree-cut | should-salvage:<what> —— 你的独立判断",
  "verified": ["实际跑的命令+结果，逐条"]
}
```
先读 SKILL.md 全文 + `court/judge.py`/`court/__init__.py`/`adapter-interface.md` §4，再核验（真跑），再出 JSON。诚实优先于礼貌。
