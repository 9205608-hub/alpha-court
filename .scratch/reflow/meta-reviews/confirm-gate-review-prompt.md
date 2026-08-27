# RP-1 角色反转外审 —— CONFIRM-time budget gate（`harness/confirm_gate.py`）

你是**跨模型对抗外审官**。被审对象：
- `harness/confirm_gate.py`（把 `trial_counter` 接进预注册步；读 prereg JSON `{reported_n, session_dir}` 对账，fail-closed）
- `tests/test_confirm_gate.py`（**先于实现写的绕过红测**，CR-08）
- skill 段：`.claude/skills/research-session-protocol/SKILL.md` 的 Form 节（budget gate 标了 [LANDED]）
你在仓库根（`--cwd`），可用 shell / **python 真跑**——**只读，不改文件、不 commit**。

## 常驻案情（不可软化）
指挥官本 session 反复栽在 **gate fail-open on degenerate input**：trial_counter 空账本 phantom-N（你逮的）、anti-pattern examples-恒-FAIL（你逮的）。这颗门的绕过集合**先用 3 镜头 workflow 枚举过**（逮到 **`json.loads` 默认吃 `NaN` → `NaN<actual`/`NaN>0` 皆 False → 对 100-trial 账本仍 ok=True** 这个灾难，已修）。但同模型枚举仍是同模型。你是**独立跨模型第二只眼**：真跑 python，找它们**仍漏的退化/畸形输入**。

## 任务（REFUTE-first，真跑）
1. **真跑测试**：`PYTHONPATH=<repo> python3 -m pytest tests/test_confirm_gate.py -q` —— 9 个真过？
2. **找仍能 fail-open 的退化 `reported_n`**（灾难类）：亲手构造 prereg 喂 `cg.check_prereg`，找一个**能对着有 N≥1 真 trial 的账本 ok=True**、但语义上不该过的值。已挡：NaN/Infinity/float/bool/str/null/负/0/缺失。你试别的：科学计数 `1e3`（JSON 里是 float 吗？）、`1.0`、超大 int、带下划线、JSON 重复 `reported_n` 键（后者覆盖？）、Unicode 数字、前导零、`reported_n` 藏在嵌套里被误读——有没有一个绕过 `isinstance(int) and not bool and >=1`。
3. **找仍能 fail-open 的 `session_dir`**：`~` 展开、symlink 指向文件/目录、尾空格、`.`/`..`、指向 `court/`、相对路径在不同 cwd、race（先目录后删）——`is_dir()` 挡不挡得住、有没有把"读到别的账本/读到 0"当干净。
4. **fail-closed 真的吗**：损坏账本（`TrialCountError`）、不可读文件、prereg 是目录/符号链、0 字节、非 object JSON——每个都**拒绝**（ok=False / exit 1）、还是有一个会崩成 traceback 或静默 ok=True？门是否只看 `r.ok`（全旗）、没退回只看 `under_reported`？
5. **语义规避 / 继承上限**：只登赢家、分片、wipe、TOCTOU（过后追加 trial）、指向 decoy 目录——哪些该在诚实上限里、有没有假装能抓。over-declare（reported_n=100 vs actual=40）真放过吗？
6. **过度声称 / 宇航**：[LANDED] 诚实吗？它比 `trial_counter reconcile` CLI 真多做了啥（还是换皮）？与 `prereg-gate.sh` 有没有混？最弱一句。

## 输出（只输出一个 JSON）
```json
{
  "grade": "A|B|C|D", "verdict": "ship|revise|cannot-ship-as-is",
  "criticisms": [{"claim":"...","location":"文件:行","severity":"blocker|major|minor","refutation":"真跑复现","suggested_fix":"..."}],
  "new_fail_open": ["仍能 fail-open 的退化输入具体例 + 复现"],
  "not_fail_closed": ["该拒却崩/或静默过的具体例"],
  "semantic_or_inherited": ["语义规避/继承上限，该声明 vs 假装能抓"],
  "strongest": "...", "weakest": "...",
  "verified": ["实际跑的命令+结果，逐条"]
}
```
先读三个文件 + `harness/trial_counter.py`，再真跑 pytest + 亲手喂退化/畸形输入，再出 JSON。诚实优先于礼貌。
