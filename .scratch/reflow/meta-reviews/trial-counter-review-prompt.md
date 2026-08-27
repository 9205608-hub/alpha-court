# RP-1 角色反转外审 —— 工位二 trial-count 对账牙（`harness/trial_counter.py`）

你是**跨模型对抗外审官**。被审对象：一颗刚建的 gate 及其红测：
- `harness/trial_counter.py`（file-backed session trial 计数 + `reconcile` + CLI）
- `tests/test_trial_counter.py`（**先于实现写的绕过红测**，CR-08）
- 相关 skill 段：`.claude/skills/research-session-protocol/SKILL.md` 的 "Form & what's mechanizable" 节（把该牙标了 [LANDED]）
你在仓库根（`--cwd`），可用 shell / git / grep / **python 真跑**——**只读，不改文件、不 commit**。

## 常驻案情（不可软化）
指挥官（Claude Code）**CR-08 已 4-for-4 栽过**：反复"建门 → 只测 happy path → 宣称是牙 → 真绕过大摇大摆走过"（reflow-gate / CR-05 / prereg-gate / git-merge-gate）。这次它声称"**先写绕过红测、还故意写 naive 版证明红测能咬**"做对了 CR-08。你的活：**别信它的自评**——独立验证红测是否真有区分力，并**找它这次又漏的绕过 / bug / 过度声称**。上一轮你（grok）在别的 skill 里逮出错数学和错 API，这类最可能重演。

## 任务（REFUTE-first，真跑）
1. **真跑测试**：`PYTHONPATH=<repo> python3 -m pytest tests/test_trial_counter.py -q` —— 5 个是否真过？
2. **验证 CR-08 区分力（关键）**：指挥官声称"故意写 naive 内存版 → happy/B1/limit 4 绿、B2 内核重启 1 红"。**你自己复现**：把 `harness/trial_counter.py` 临时换成一个内存 dict 版（或在你的会话里模拟），确认 `test_bypass_kernel_restart_accumulates` 对内存版**真的红**、对文件版**真的绿**。若这条测试其实内存版也能过（区分力是假的），那是 blocker。
3. **`reconcile` 逻辑 bug**：over_budget = actual > declared_k；under_reported = reported_n < actual；ok = not(over or under)。找反例：有没有该报不报 / 不该报乱报的输入？（如 reported_n > actual 是否正确放过？declared_k 与 reported_n 不一致时？arms<1？畸形 ledger 行？空/不存在 session_dir？并发 append?）
4. **找我没说的绕过（最重要）**：诚实上限我只列了三条（计数是下界/NIH 不可见/账本可手改）。**还有哪些绕过我漏了？** 例如：把一次搜索**分片到多个 `session_dir`**、各自 reconcile against 小 K 都过（真跑了 40 却分两 dir 各报 20）；或指向新空目录；或 reconcile 时报个大 declared_k。逐个给出并说该不该补红测/补上限声明。
5. **两个"ledger"会不会混淆**：`trial_counter` 的 `trial-ledger.jsonl`（session 搜索计数）vs `court.Ledger`（court 判决读的 trial 注册表）——skill/代码有没有把这俩搞混、或让读者以为是同一个？（上一 session 我刚因"honest N=empirical-null pool"被你判 court 概念串线。）
6. **过度声称 / 宇航**：一个 json-lines 计数器，[LANDED] 声称有没有夸大？诚实上限措辞有没有把缺口洗成美德？最弱一句。

## 输出（只输出一个 JSON）
```json
{
  "grade": "A|B|C|D", "verdict": "ship|revise|cannot-ship-as-is",
  "cr08_discrimination": "real | fake:<why> —— 你复现内存版后的独立结论",
  "criticisms": [{"claim":"...","location":"文件:行","severity":"blocker|major|minor","refutation":"查到的反证/复现","suggested_fix":"..."}],
  "missed_bypasses": ["我漏掉的绕过 + 该补红测还是补上限声明"],
  "reconcile_bugs": ["reconcile/record/count 的逻辑或边界 bug + 反例"],
  "strongest": "...", "weakest": "...",
  "verified": ["实际跑的命令+结果，逐条"]
}
```
先读三个文件，再真跑 pytest + 亲手复现内存版对 B2 的红，再找绕过/bug，再出 JSON。诚实优先于礼貌。
