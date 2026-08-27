# RP-1 对抗审：resume-preflight 牙 + 验收预检测 + 冻结词表增条提案

你是 grok，fresh session，对 alpha-court 的三件指挥官自产物做 REFUTE-优先的外审。
只读 worktree（HEAD=`4dc644bc`），可以且应该**亲跑**测试与脚本。你的任务是推翻，
不是背书；每条发现必须带 file:line 或亲跑输出作证据。

## 审件 1 — `scripts/resume-worker.sh` + `tests/test_resume_preflight.py`（CR-13 牙）

背景：`bridge-isolation-failure` 第二次复发（工人派单工树被删、裸 `grok --resume`
无守卫、交付直落生产分支——案卷见 `.scratch/reflow/commander-rework/CR-13-*.md`）。
此脚本 = resume 预检（fail-closed）+ 后置绊线。16 条绕过红测先行（枚举见测试
docstring），实现后全绿，全套件 550。

请做：
1. **亲跑** `PYTHONPATH=. python -m pytest tests/test_resume_preflight.py -v`（用
   worktree 里可用的 python + pytest；无 venv 时可自建）。
2. **构造枚举外的绕过**——重点镜头（指挥官自报的弱点，别客气）：
   - 绊线的 `grep -vF basename` 过滤：工人在 checkout 其它位置写**同名文件**是否被
     误豁免？值不值一条红测？
   - macOS **大小写不敏感 FS**：case-变体路径过 `os.path.realpath` 后，repo-containment
     与 allowlist 前缀的字节比较各自失败方向是 false-reject 还是 escape？（V17 家族）
   - `DISPATCH_WORKTREE_ROOT` 本身被 symlink 进 repo 内的场景算 config-fault 还是该防？
   - receipt JSON 里 `worktree_path` 为**非字符串**（数组/对象/数字）时 python 段行为？
   - 还有别的吗——你赢过这类题（symlink-DIR、evil.PY、trunk 改名都是你逮的）。
3. **诚实标签核查**：脚本头与测试 docstring 的"declared-not-defended"清单是否
   把真窟窿说小了（detection-not-prevention 的表述准不准）？

## 审件 2 — `tests/test_acceptance_preflight.py`（互评 TC2 的机械化，CR-07：指挥官自产门须外审）

主张：①现表 2 测全绿；②对历史冻结表 `c987a5b9` 会红（missing=[3.0]），指挥官已
独立复算。请核：测试是否**空转**（比如 PowerConfig 默认值变了它还测不测得到东西；
FROZEN 路径写死对不对；strength_grid 那条是不是恒真）；历史红的复算你亲自再跑一遍
（`git show c987a5b9:.scratch/v0.2/power-frozen/calibration.json`）。

## 审件 3 — `.scratch/reflow/vocab-proposal-2026-07-20.md`（冻结词表三增条）

词表冻结规则：**拆分词条 = 指挥官把复发洗回 n=1 的标准手法**，增条须过你这关。
逐条裁：genuinely-new / respell-of-existing（若 respell，指明该给哪个现有 id
occurrences += 1）。表内已写"最近似现有 id 及为何不同"，专门供你推翻。

## 输出要求

最终输出必须且只能是一个 JSON 对象：
`grade`（A-F，对三件整体）、`item1_findings`（数组：{severity: blocker|major|minor,
claim, evidence, suggested_fix}）、`item2_verdict`（{vacuous: bool, historical_red_confirmed:
bool, findings: []}）、`item3_vocab_ruling`（数组，每提案条：{id, ruling: new|respell,
respell_target?, reason}）、`honest_labels`（declared-not-defended 清单评价）、
`summary`（≤200字中文）。
