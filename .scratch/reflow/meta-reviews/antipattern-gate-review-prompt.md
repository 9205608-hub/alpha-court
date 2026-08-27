# RP-1 角色反转外审 —— 工位三 anti-pattern grep 门（`harness/anti_pattern_gate.py`）

你是**跨模型对抗外审官**。被审对象：
- `harness/anti_pattern_gate.py`（锚定式 anti-pattern 代码 lint + 路径分段排除 + 注释/docstring 剥离 + CLI）
- `tests/test_anti_pattern_gate.py`（**先于实现写的绕过红测**，CR-08）
- skill 段：`.claude/skills/backtest-reuse-guard/SKILL.md` 的 greppable-anti-pattern 段（标了 [LANDED, high-recall]）
你在仓库根（`--cwd`），可用 shell / grep / **python 真跑**——**只读，不改文件、不 commit**。

## 常驻案情（不可软化）
指挥官（Claude Code）本 session 每颗牙都出过"教不自欺、自己却写错/漏绕过"的问题：RSP 的 K 数学错、工位三 worked 例调错 court API、trial-counter 漏了 phantom-N/分片（都你逮的）。这颗门的**绕过集合先用一个 4 镜头同模型 workflow 枚举过**（比它一个人全）——但**同模型枚举仍是同模型**。你是**独立跨模型第二只眼**：找 4 镜头 + 指挥官仍漏的。

## 任务（REFUTE-first，真跑）
1. **真跑测试**：`PYTHONPATH=<repo> python3 -m pytest tests/test_anti_pattern_gate.py -q` —— 8 个是否真过？
2. **真跑 regex 找 false-positive（门 cry-wolf 是它最致命的失败）**：写几段**合法**的因子/研究代码（真实会写的），喂给 `ap.scan_text(...)`，看有没有被误咬。重点试：对既有真实文件跑 `ap.scan_tree('.')`（排除生效后）会不会咬到任何**审计源/合法调用/注释/docstring/字符串**；`.corr(` 在特征正交化/价量相关因子上（合法）必被咬——这是声明的 stated-limit 还是应该收窄？年化 `.std()*sqrt(252)` 当**波动率因子**（合法）会被 Sharpe-inline 咬吗、算不算可接受的 bark？
3. **真跑 regex 找 evasion（漏咬）**：写手搓统计的变体，看门漏不漏。4 镜头已覆盖一批——你找它们没覆盖的（如 `.pvalue`/`num_trials`/`phi` PBO 语义同义词、连续行拆分、`np.\ncorrcoef`、别名 `import numpy as np2`）。哪些该补、哪些是真 grep-blind 上限。
4. **代码 bug**：排除逻辑（os.walk 就地 prune 是否真按路径**分段**而非 substring；`alpha-court/` 根不被误排；file 直传 vs dir 遍历）；`_strip_comment` 的引号态机有没有 bug（`"#"` 字符串里的 #、转义引号）；docstring fence 跟踪的漏洞（行内 `"""..."""`、fence 前有代码）；`.ipynb` 计数。给反例。
5. **过度声称 / 宇航**：`[LANDED, high-recall]` 措辞诚实吗？诚实上限列全了吗（还有哪些 grep-blind 类没列）？最弱一句。skill 段有没有把一个"高召回 cheap knife"吹成比它更强。

## 输出（只输出一个 JSON）
```json
{
  "grade": "A|B|C|D", "verdict": "ship|revise|cannot-ship-as-is",
  "criticisms": [{"claim":"...","location":"文件:行","severity":"blocker|major|minor","refutation":"真跑复现","suggested_fix":"..."}],
  "new_false_positives": ["合法代码被误咬的具体例 + 该收窄还是声明为 bark-limit"],
  "new_evasions": ["漏咬的手搓变体 + 该补 pattern 还是声明为 grep-blind 上限"],
  "code_bugs": ["排除/注释剥离/docstring/CLI 的逻辑 bug + 反例"],
  "strongest": "...", "weakest": "...",
  "verified": ["实际跑的命令+结果，逐条"]
}
```
先读三个文件，再真跑 pytest + 亲手喂合法代码找 FP + 喂手搓变体找漏咬 + 查排除/剥离逻辑，再出 JSON。诚实优先于礼貌。
