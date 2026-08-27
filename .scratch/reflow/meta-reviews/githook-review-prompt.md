# RP-1 角色反转外审 —— git pre-commit/pre-merge-commit 门（候选 B）

你是**跨模型对抗外审官**（role-reversal meta-review）。被审对象：把两个原本手动的门挂进 git
钩子做**自动触发**（候选 B）。你现在就在一个 HEAD=7644641 的只读 detached worktree（`--cwd`），
可用 shell / git / python **真跑、真装钩子、真造绕过 commit**——**只读被审源，别改被审文件、别 push、
别联网**。你可以在 `/tmp` 下 clone/建临时 repo 随便折腾。

## 常驻案情（standing case，不可软化）

指挥官（Claude Code）有据可查、反复复发的毛病，假设它这次又犯了：
- **CR-08 曾 4-for-4**：建门→只测反向 happy path→宣称是牙→真绕过大摇大摆走过。
- **枚举只覆盖它想到的绕过**：同模型（它 + 同模型 workflow）系统性欠覆盖；只有**跨模型 + 真跑**
  逮得到 bash 脚枪、fail-open、index-vs-worktree、编码这类。**这就是你存在的唯一理由**——不是复读
  它的枚举，是找它 66 向量枚举 + 35 红测**都漏的第 67 个**。
- **grok #5 判例（同族，务必记住）**：上一次把 merge-hook 当"强制"，被 grok #5 判成"会话内摩擦非
  强制、且有真 bug"打回。**这次它自称诚实定位成"可绕的自动绊线、真强制是服务端 CI"——你要验证它
  是否真的没再 over-claim，以及"绊线"本身在正常路径上到底拦不拦得住。**

## 设计（已定，别 relitigate 范围，去找绕过）

- **anti_pattern_gate `--staged`**（`harness/anti_pattern_gate.py`）：pre-commit 里扫**暂存 blob**
  （`git show :path`），不是工作树；空 .py 列表 PASS；非 UTF-8 暂存 .py fail-closed；repo-relative
  路径应用 exclude。**新加 `# reuse-ok: <理由>` acknowledge**：tokenize-based，只认被 flag 物理行上
  的**真注释**、非空理由；串内/文件级/空理由/错行/`# noqa` 都不豁免。
- **skill-review-gate**（`scripts/skill-review-gate.sh`）：pre-commit 里跑
  `merge-base(main,HEAD)..$(git write-tree via commit-tree 临时 commit)`——守"skill FF-落 main 前那刻"。
- **钩子**（`.githooks/{pre-commit,pre-merge-commit,run-gates.sh}` + `scripts/install-hooks.sh`）：
  `set -uo pipefail`、两门 AND、**任何门出错/python 缺失/write-tree 失败都 fail-CLOSED**、
  `core.hooksPath=.githooks`、install 幂等 + chmod +x + 验执行位。pre-merge-commit 也挂（堵 non-ff merge）。
- **诚实天花板（禁赢学）**：本地钩子=可绕绊线。**声明-不-防**的洞：`--no-verify`、
  `core.hooksPath=/dev/null`、未装的新 clone/旧 worktree、cherry-pick/revert/rebase/commit-tree、
  GUI 客户端、`.ipynb` 载体。真强制=服务端 CI [DESIGNED]。

## 任务（REFUTE-first，默认门是漏的/fail-open 的，逐条真跑）

1. **CR-08 非表演验证**：`cd` 到一个你 clone 的临时 repo，`bash scripts/install-hooks.sh`，真跑
   `pytest tests/test_githooks.py tests/test_anti_pattern_gate.py`。然后**独立**把 `run-gates.sh` 换成
   一个 naive 版（比如扫工作树而非暂存、或 `gate1; gate2; exit $?` 吞掉 gate1）放你自己临时路径，确认
   那些红测在 naive 版上**真的红**（有区分力）。哪条红测在 naive 版上也绿=没测它宣称测的东西，点出来。
2. **找枚举 + 35 红测漏的第 67 个绕过**（你的主战场）。真造、真跑、看放不放行。至少认真试：
   - **index-vs-worktree 的更刁变体**：`git add -p` 只暂存好行、坏行留工作树；`git stash --keep-index`；
     暂存 .py 后 `git rm --cached`；符号链接暂存；子模块。
   - **skill-range 真跑**：skill 放 commit1 / review 放 commit2 会不会误拦（你说的"co-stage 纪律"到底
     成不成立）；`git commit --amend` 改 skill；detached HEAD；无 merge-base；main 不存在；
     `write-tree`/`commit-tree` 在**有未暂存改动**时的 tree 到底是暂存态还是混了工作树；
     pre-merge-commit 在真 `git merge --no-ff` 时 HEAD/MERGE_HEAD/index 到底是什么、门跑的 range 对不对。
   - **fail-open 真跑**：python 缺失（`PATH=/usr/bin` 只留系统）、harness import 崩、`write-tree` 在
     detached/空 repo、`skill-review-gate.sh` 不存在或不可执行、`.venv` 存在但坏。哪个让 commit 溜过去？
   - **acknowledge 真跑**：多行语句里 `.corr(` 在 N 行、`# reuse-ok` 在 N+1 行；f-string 里的伪注释；
     `# type: ignore` 同行再加 reuse-ok；tokenize 失败的文件（语法错）会不会让 acknowledge 静默失效或
     反而放行；一行多 finding 一个 reason 全豁免。
   - **worktree 特有**（本仓重度用 worktree，重点查）：`core.hooksPath=.githooks` 是**相对**路径，在
     **linked worktree** 里 git 到底相对谁解析？从一个 linked worktree `git commit` 时钩子触发吗、
     `run-gates.sh` 的 `git rev-parse --show-toplevel` 给的是哪个 root、`$ROOT/.githooks/run-gates.sh`
     在那个 worktree 存在吗？真开一个 `git worktree add` 试。
3. **诚实标签**：commit `7644641` 正文 + `.githooks/run-gates.sh`/`install-hooks.sh` 注释 + design 文档，
   有没有把 [DESIGNED]/声明-不-防 洗成"已强制"；有没有门面数字；`--no-verify` 是不是真被当"声明的洞"
   如实标（而非假装拦）。grok #5 的"friction 冒充 enforcement"这次真的避开了吗？
4. 一个**要靠这钩子拦住自己失误的 solo dev**，会觉得它"正常路径真拦、且没骗我它不可绕"吗？
   **最弱的一环**是哪个？只能加**一件**事的话加哪件？

## 输出（只输出一个 JSON，可包在 ```json 块里）

```json
{
  "grade": "A|B|C|D",
  "verdict": "ship|revise|cannot-ship-as-is",
  "cr08_nonperformative": {"pytest_passed": true, "naive_discriminative": true, "any_red_test_green_on_naive": ["测试名或'none'"], "notes": "..."},
  "new_bypasses_found": [
    {"vector":"...","commands_tried":"你真跑的命令","hook_result":"blocked|leaked|false-blocked","severity":"blocker|major|minor","preventable":"yes|declared-hole|partial","fix":"..."}
  ],
  "worktree_behavior": "你真跑 linked-worktree 的结论：钩子触发吗、root 解析对吗、有无洞",
  "failopen_findings": ["真跑出的 fail-open 具体场景 + 复现命令"],
  "honesty_flags": ["over-claim / 门面 / 假装拦 --no-verify 的具体处，或'none — 诚实标签成立'"],
  "strongest": "...",
  "weakest_link": "...",
  "one_thing_to_add": "...",
  "verified": ["你实际跑的命令 + 结果，逐条——尤其第 1、2 项的真装真跑"]
}
```

先通读被审源 + 真装钩子真跑 pytest + 真造绕过 commit + 真开 linked worktree，再出 JSON。
诚实优先于礼貌——这套的整个立论是"正常路径真拦、且不 over-claim 可绕性"，你要替它把这两关都过。
