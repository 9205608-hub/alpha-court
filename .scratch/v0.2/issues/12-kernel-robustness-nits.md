# 12 内核 robustness nits 批处理（v0.1 审计 minors，低优先）

Type: task
Status: resolved (2026-08-12 RP-1 complete: ACCEPT + 4 findings adjudicated, remediation landed — see Answer)
Triage: ready-for-agent
Label: wayfinder:task

## Question

v0.1 审计 Claude 架构镜头抓的一批**低优先 robustness nits**，逐条捕获以免静默丢弃
（禁赢学）；不阻塞任何 v0.2 主线，可择时批量清理（TDD 红绿，每条一小 slice）：

1. **撕裂恢复混用字符/字节偏移**（`court/ledger.py:261-267, 305-310, 406`）：`line_spans`
   按解码 str 的 `len()`（字符数）算，却传给二进制 `f.truncate(nbytes)`——**只因
   `json.dumps` 默认 `ensure_ascii=True` 才对**。补一条钉死 `ensure_ascii=True` 的断言/
   测试，或改为按原始字节 split 做字节精确恢复。
2. **judge.decisions 按 statistic 名做键**（`court/judge.py:82-84, 148`）：同一 config 里
   同名 statistic 两次 application 会**静默互相覆盖**摘要。改按 verdict_id 或
   `(statistic, index)` 键，或返回逐 application 列表。
3. **replay 比写路径更轻信**（`court/ledger.py:340, 362-384`）：`_apply_event` 在
   `corrupt_on_error` 下不复验 declared 字面量与 decision 词表（写路径会验）。让 replay
   跑同一套校验器，损坏证据 fail-closed。
4. **create/truncate 无父目录 fsync**（`court/ledger.py:247-249, 305-310`）：内容 fsync 有、
   目录项 fsync 无——"落盘即预注册时间戳"的持久性承诺（契约 §7.1）在崩溃窗口略虚。补
   父目录 fsync。
5. **from_panels 用 `object.__new__` 手抄属性**（`adapters/qlib_cn.py:427-464`）：与
   `__init__` 重复设一遍全部属性，新增 `__init__` 属性会**静默失步**合成路径。抽一个共享
   `_finalize(...)` 两个构造器都调。
6. **verdicts() 文档/死子句**（`court/ledger.py:585-591`）：docstring 说按 scope 过滤，
   代码还多匹配 `decisions`——因 `decisions ⊆ scope` 恒成立而是死子句。删子句或改文档述明
   `scope ⊇ decisions` 不变量。

## 验收标准

- 每条一小 TDD slice（能红先红）；相关测试零回归；ruff 净。
- 可分批 resolve；本票允许部分完成后拆余项，或逐条勾除后统一关票。

## 审计修订（2026-07-12）

- 与 06 的边界：**存储行序列化保持 v0.1 字节语义不动**（撕裂恢复依赖它）；`sort_keys`/
  float 编码只存在于 06 的哈希路径。12 的任何序列化 nit 不得触碰 06 落的链字段。
- 顺序：12 押后于 06/08/09 批处理（map 冲突矩阵）。

## 追加项（2026-07-13，08 收货探针面板 ⚠ + nits 归批）

- **replay 侧 role 值域校验**（08 收货唯一 ⚠，轻 contract-fault——票面只钉了 append 侧）：
  `court/ledger.py` verdict replay 分支 `event.get("role")` 对垃圾值照单全收（伪造合法链
  注入 `"banana"` 可读出）。方向性安全（聚合把未知值当 discriminating——更严分支，无
  放水通道），但与 append 侧不对称。修法：replay 加同一行值域校验（fail-closed 对称）。
- 08 收货 nits 顺手批：`_resolve_pbo_metric` 后的 registry 复查不可达分支（死代码可留可删）；
  同质性守卫 N 次单查 `ledger.trials([tid])`（微效率）；两个 caller-form 测试的
  `match="metric"` 判别力弱（可收紧到新错误文案）。
- 09 收货 nits 归批（2026-07-13）：`AggregationPolicy.params` 按引用存储可绕构造期
  `=={}` 不变量（`to_payload` 硬编码 `{}`、apply 不读 params，实害≈0；防御性 copy 或
  MappingProxyType）；`from_payload` 静默忽略未知键（若 ⚠-2 走"07 原文比较"路线则此条
  可保持并披露，若走拒收路线则在此修）。
- 07 收货 LOW（2026-07-13→16 rework-02 探针，worker-fault 轻）：`harness/verify.py:550`
  的 `main` 只 `except ValueError` 包 `_parse_anchor_arg`，畸形 `--anchor
  file:<父目录非目录>`（如 `file:/dev/null/foo`）使 `FileAnchor.__init__` 的 `mkdir`
  抛 `FileExistsError`（OSError 子类）逃逸成 traceback——仍 exit 1 fail-closed、验证者
  自敲、伪造面不可达。一行修：放宽为 `except (ValueError, OSError)`。附带：FileAnchor
  create-on-construct 让名义只读的 verify 产生 mkdir/touch 副作用，同处留意。
- 10a 收货 nit（2026-07-17，无害）：`scripts/dispatch_receipt.py` 写 receipt 时加尾换行
  （原 heredoc `json.dump` 不带），POSIX 正向但属未在 notes 点名的字节差异。可留可去。
- **架构 observation（07/09 引入，非 nit——值得单独评估）**：`harness/__init__.py` 现
  eagerly import court.judge（CertifiedRun/AggregationPolicy 等导出链）。副作用：`import
  harness`（含 `-m harness.<任何子模块>`）在 court/ 不可从 cwd 解析的环境里会炸（court_import_gate
  staged 测试正是被此咬，已 `-P` 绕过）。真实 git 钩子从 repo 根跑不受影响，但 harness 包不该
  强依赖 court.judge 可从任意 cwd import——考虑 `__init__` 惰性导出（`__getattr__`）。

## Answer（2026-07-31，指挥官实施 + 逐项裁定）

**8 个代码 slice 全部落地（commit `610f9f82`，每 slice 红测先行）**：
A 撕裂恢复字节精确化（含 ASCII 存储钉）/ B 回放-写入四处校验对称 +
decisions⊆scope 双侧 + verdicts() 死子句删除 / C Judgment.decisions 改
verdict_id 键（judge + run 两处，payload 未知 vid fail-closed）/ D 建档父目录
fsync / E 适配器 _finalize 共享收尾（from_panels 部分 mask 计数真失步已修）/
F verify CLI 捕 OSError / G params 防引用逃逸 / H 两处 match 收紧。
全量 556 绿（基线 542 + 新 14）、ruff 净、解耦门 PASS、committed 产物新校验下
回放全绿。

**记录性裁定（不动代码，防静默丢弃）**：
- `_resolve_pbo_metric` 后的 registry 复查分支：**保留**——它守的是
  `_BASE_METRICS` 与 `_METRIC_REGISTRY` 两张手维护表未来漂移，今日不可达 ≠
  永远不可达。
- `ledger.trials([tid])[0]` N 次单查微效率：**保留**（13/14 号提速后非热路径）。
- `AggregationPolicy.from_payload` 未知键宽容：**保留并披露**——⚠-2 已走
  "原文比较"路线（`harness/verify.py:336` seal 与链上声明整字典逐字相等），
  未知键无法在 seal/declaration 间分叉。
- `dispatch_receipt.py` 尾换行：**保留**（POSIX 正向）。
- `harness/__init__` eager import court.judge（架构 observation）：**评估后缓建**
  ——真实调用（repo 根 + git 钩子）不受影响、`-P` 绕过已在位，认证路径包初始化
  重构不值得混进 nits 批；留给 v0.3 议程。

**归因**：grok 配额中断（原 session turn 12 被 Cancelled，resume 撞 free 限额）
= **tooling-fault（infra），零 worker-fault**——工人被中断前的 Slice A 未提交
产物**未读弃用**（保持指挥官实施的独立性）。dispatch.sh sessionId 打印 bug
（f-string 表达式内反斜杠转义 = SyntaxError，致成功派单误报 exit 1）为本次
连带修复（`828e9363`）。**grok RP-1 跨模型审查 = 本票唯一未了项**，配额恢复后
对 `610f9f82` 做对抗复核，赶在快照发布前；工人工树
`~/.alpha-court/dispatch-worktrees/v0.2-12-robustness-nits-20260731-004153`
留作审计现场，RP-1 完成后清理。

## RP-1 收货裁定（2026-08-12）

**审查执行**：grok（新 Heavy 账号）对 `610f9f82` 只读审计，两段式（配额中断一次
resume 续跑，工树 `v0.2-12-rp1-review-20260812-232459`，final diff 空、绊线净）。
**总判 ACCEPT**：A–H 逐 slice 过；A/B/C 红测证据由审查方在旧基座独立复立
（新测在 52566a27 生产代码上真红）；活攻击未破 A 恢复与 C 改键；全套件/ruff/门
独立复跑全绿。4 findings 逐条裁定（referee 6/6 探针亲复现后采纳）：

1. **[major] series 回放轻信**（采纳，integrity 修复入 remediation commit）：
   `record()` 走 `_validate_series` 而回放只 `_series_from_dict`——长度错配/空
   序列/NaN/重复标签的伪造账本全数回放成功。**归因 contract-fault（指挥官）**：
   冻结 B 清单枚举不全（列了 declared/decisions/role/scope 漏了 series）——
   同一人建+审的盲区被跨模型审查逮住，RP-1 机制首次在"指挥官代建"场景下实证。
2. **[minor] verdict 空 scope/空 statistic 回放不对称**（采纳，同 commit 修复）。
3. **[minor] ASCII 钉非红先**（按文档裁定：票面与 commit message 均声明其为
   pin 而非红证据，A 的红证据是两个恢复测试——无行动，审查方 deviation 自注
   与此一致）。
4. **[minor] court-kernel-spec.md Judgment 注释未随 C 改键**（采纳，同 commit
   一行修复）。

**receipt 形态偏差记录**：resume 无 --json-schema 兜底，self_test 命令字段
序列化为 null（证据文本在 findings/deviations 中完整）——工具侧已知限制，
不影响裁定。整改 6 测红先行、562 全绿。**RP-1 过闸，快照发布前提解除。**
