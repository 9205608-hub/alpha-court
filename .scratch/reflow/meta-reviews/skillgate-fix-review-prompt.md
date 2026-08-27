# RP-1 角色反转外审 —— skill-review-gate 范围级假 PASS 修复（`scripts/skill-review-gate.sh`）

你是**跨模型对抗外审官**。被审对象：
- `scripts/skill-review-gate.sh`（改后：每个改动 skill 的 `<name>` 须在 review 的 **added** 行里、词边界匹配）
- `tests/test_skill_review_gate.py`（**先于修复写的绕过红测**，CR-08；建临时 git repo 跑真门）
你在仓库根（`--cwd`），可用 shell / git / bash **真跑**——**只读，不改文件、不 commit**。

## 常驻案情（不可软化）
指挥官反复栽在 **gate 假 PASS**：这颗门原本范围级 co-presence 被**不相关** review 满足（两个新 skill 曾靠案例文 review 蒙混）。绕过集合**先用 2 镜头 workflow 枚举**（逮到子串 `research`⊂`research-session-protocol`、旧-review-touch、omnibus 顺带点名）。但同模型枚举仍是同模型。你是**独立跨模型第二只眼**：真跑 git，找**仍漏的**。

## 任务（REFUTE-first，真跑）
1. **真跑测试**：`PYTHONPATH=<repo> python3 -m pytest tests/test_skill_review_gate.py -q` —— 8 个真过？
2. **真跑门找仍能假 PASS 的**：亲手建临时 git repo（或用真 repo 的 commit 造 range），构造"改了 skill 但没有真覆盖 review 却 PASS"的场景。已挡：不相关 review、子串、旧-touch、多 skill 部分覆盖。你试别的：
   - review 在 range 的**更早 commit**加、skill 在**更晚** commit 改（added 行方法算不算覆盖？）；
   - MODIFIED（非 ADDED）的 review、review 跨 RP-1 迭代更新、skill 名在旧内容不在 delta；
   - 词边界正则 `(^|[^A-Za-z0-9_-])${name}([^A-Za-z0-9_-]|$)` 的边角：name 在行首/行尾、name 含正则元字符（skill 名理论上能否含 `.`/`*`——`${name}` 未转义有无注入/漏匹配）、CJK/unicode skill 名、大小写；
   - `--diff-filter=d` 行为、rename(R)、added-then-deleted、`git show` 失败、base/head 分支带斜杠、reversed。
3. **误伤（over-block）**：有没有**真该过**却被挡？真跑本 repo 四次真实 merge range（trial-counter/anti-pattern/confirm-gate/stations 的正向 range）确认仍 PASS；原 `1ce25a7` sin 仍 FAIL。
4. **bash 正确性**：`${name}` 插进 grep -E 的注入/元字符、`while IFS= read` + heredoc、`set -uo pipefail` 与 `grep || true` 的交互、review_added 为空时的行为、`printf '%s\n'` 边角。
5. **过度声称 / 宇航**：header 的诚实上限列全了吗（common-word/omnibus/active-fake 之外还有？）？"修好了范围级假 PASS"是否夸大（它只是把门槛从"任意 review"抬到"点名该 skill 的 review"，非"真覆盖")？最弱一句。

## 输出（只输出一个 JSON）
```json
{
  "grade": "A|B|C|D", "verdict": "ship|revise|cannot-ship-as-is",
  "criticisms": [{"claim":"...","location":"文件:行","severity":"blocker|major|minor","refutation":"真跑复现","suggested_fix":"..."}],
  "new_false_pass": ["仍能假 PASS 的具体 git 场景 + 复现"],
  "over_block": ["真该过却被挡的具体例"],
  "bash_bugs": ["注入/元字符/边角 bug + 复现"],
  "strongest": "...", "weakest": "...",
  "verified": ["实际跑的命令+结果，逐条"]
}
```
先读门 + 测试，再真跑 pytest + 亲手造 git range 探测，再出 JSON。诚实优先于礼貌。
