# Panel B report — 机制/威胁模型镜头（Claude 独立面板，盲审）

> 面板员全程未见 grok 输出与指挥官 seam 清单（盲审）。原文如下，一字未改。

# v0.2 设计层审计 — 面板员 B（机制/威胁模型镜头）

## 总评

- **`docs/design/prereg-gate.md`（02）：修后施工，C+。** 机制骨架是对的（物理行序为根、内容哈希链、harness 派生 scope、agent 不递 scope），但认证语义有一处**字面自相矛盾**（锚时序）、一处**核心不变量左边不存在**（attested == declared），且 §6 诚实边界漏掉了三条最自然的自欺路径（认证路外预筛、截尾删除、run 拆分）——对一个把"不骗自己"写进宪法的项目，§6 不完备本身就是最重的罪。
- **`docs/agents/dispatch-and-governance.md`（10）：修后施工（轻），B+。** 诚实、克制、YAGNI 判断正确，纯纪律处如实 declared；唯 receipt schema 验证机制缺位使"最小工人契约"对第二个 CLI 并不闭合，另有两处小盲点。

---

## Findings（按严重度）

### BLOCKER-1：§4.3 与 §5 的锚时序字面矛盾，按原文无法实现

**契约**：prereg-gate.md §4.3 vs §5 末条 vs §7。
**证据**：§4.3："The external anchor is pinned **once, at seal**"（seal 在一切 series 之后）。§5 末条："(when an anchor is required) an anchor that does **not predate the series** → seal invalid"——即合法性要求**锚早于 series**。两句同真则每个带锚的 sealed run 都无效。§7 引的个人工作流先例（"results not before the pre-registration commit"）是**锚在前**语义（锚=预注册提交，结果不得早于它）；§4.3 是**锚在后**语义（锚=封印时的重写防护）。§5 把锚在前的检查条款抄进了锚在后的设计里。
**失败场景**：07 的工人二选一实现——按 §5 实现则 fail-closed 检查恒触发或工人擅自反转不等号；按 §4.3 实现则 §5 该条款成死代码，且"backdate 会被抓"的测试承诺（§9）失去唯一可能的机制载体。
**不改的后果**：这是四步派单链（06→07）的正门条款，工人必然各自臆断，裁定时变成 contract-fault。修法：§5 该条改为"seal 必须是账本末事件；锚必须覆盖 seal 前的 chain_head；锚定后出现任何追加 → verify 失败"；若要锚在前语义，须另设 run 创建时的可选前锚，两种锚各自命名。

### BLOCKER-2：conformance 等式 "attested == declared" 有一半字段没有 declared 侧；"sanctioned adapter" 无任何锁定机制

**契约**：prereg-gate.md §2 Q4、§5 第三条、§3。
**证据（逐字段对账）**：attested 侧真实存在——`adapters/qlib_cn.py:476-506` `_meta` 含 `metric / window / universe / n_evaluation_dates / data_version{declared_tag,calendar_end,n_instruments} / qlib_version / adapter_version / config{provider_uri,label_expr,quantile,min_cross_section,...}`，契约 §3 的声称属实 ✓。但 declared 侧（spec §5.7 / `court/ledger.py:45-52`）`DeclaredProtocol` 只有 `metric / window / periods_per_year / direction / se`——**没有 universe、没有任何 \*_version、没有 n_evaluation_dates**。等式对 metric/window 可比，对 §5 自己点名的 universe 及 Q4 点名的 *_version/n_evaluation_dates，**左边不存在**。且 trial-ledger.md §10 承诺"v0.2 gate adds enforcement, not fields"、02 §3 承诺"court/ unchanged"，堵死了扩 `DeclaredProtocol` 的路；塞进 `spec`（court 不解释的自由 dict，agent 全控）则无法 fail-closed。契约没有给这三类字段指定任何 declared 家。
**攻击场景**：更深一层——`provider_uri / label_expr / quantile / min_cross_section / declared_data_tag` 定义了"地面真相是什么"，它们被如实 attested 进 `meta.config`，但 §5 不检查它们、也没有任何条款要求整个 run 使用同一 adapter 配置。agent 在一个 run 内逐 trial 换 `label_expr`（换前瞻收益定义）或换 `provider_uri`（换数据包），窗口相同则 `matrix()` 对齐照过、§5 全绿、seal 有效——**协议被锁住了，但世界没被锁住**。
**修法（一举两得）**：run 创建时上链一个 `run_config` 声明事件，锁定完整 adapter 配置（含 universe、data tag、label_expr）；conformance = 每次 attestation（含 meta.config）== run_config。universe/*_version 从此有了 declared 侧，且不动 `DeclaredProtocol`、不违反"court unchanged"。这需要在冻结契约里写明，否则 06/07 两个工人会发明两套不兼容 schema。

### major-1：后缀截尾 = 零痕迹藏尸，实测真代码无声通过；§9 的"tamper → verify fails"承诺对删除不成立

**契约**：prereg-gate.md §4.3、§6（未披露）、§8、§9。
**证据（实跑）**：对真 `court.Ledger` 注册 2 trial、record 2 evaluation 后，删除最后一行 evaluation 事件再 `Ledger.open()`——回放零报警，t2 从 `evaluated` 静默回到 `registered`：

```
before attack: evaluated evaluated
after attack:  evaluated registered | open() raised: NO
```

哈希链对此无力：链只承诺前缀完整性（无前向承诺），任何前缀都验证通过；§4.3 的 torn-write 恢复规则把"截尾"合法化为崩溃恢复；外锚**在 seal 之前不存在**，整个 run 中途是无锚窗口。截掉的 trial 按 §8 的 file-drawer 语义"not in the series-derived N"——评估过、看到坏结果、截掉证据，账本与诚实的"注册后未评估"**逐字节不可区分**。
**失败场景**：这正是威胁模型第一条"hiding trials"，而 §9 承诺的测试是"tamper one **line** → verify fails"——对改写为真、对删尾为假；§6 三条边界没有一条披露它。
**不改的后果**：demo 讲出去的"无法藏 trial"是假话（禁赢学违规）。最低修法：(a) §5 补"seal 必须是末事件"（封 seal 后截尾）；(b) §6 补第四条：**seal 前窗口无锚，蓄意截尾无痕，chain 只证明幸存行的顺序一致性**；(c) 可选机制：Run 对象存活期内禁止从磁盘重派生 head（只防单进程内），或周期性轻锚（已被 §4.3 拒绝，那就必须披露）。

### major-2：认证路外预筛洗白——§1 的目的宣言被自己的 Q2 裁决否定，且 §6 不披露

**契约**：prereg-gate.md §1 vs §2 Q1/Q2、§6。
**证据**：§1 声称 gate 要堵的正是"nothing enforces that the family the court judges is **the full search the agent ran**"。但 Q2 把直接调 adapter/court 正式命名为"**legitimate** uncertified calculator use"。攻击：agent 在认证路外扫 1000 个变体（合法！无 seal 但也无人要求 seal），挑 5 个赢家开一个全新 certified run 注册评估，拿到**完全有效的 seal，N=5**。机制真正交付的是"family = 经过这个 Run 对象评估的集合"，不是"agent 跑过的全部搜索"。这是真实预注册制度同款的第一大漏洞、也是自欺 agent 的最自然路径——certified run 在此**主动提供假安慰**。
**不改的后果**：v0.3 的 idea-mining agent 会诚实地走完认证路并诚实地欺骗自己。修法：§1 措辞收窄为"the full search run *through the certified path*"；§6 补第五条边界，指明 RP-1/审阅人须追问"这个 run 之前你在同一数据窗口上碰过什么"（可要求 certified run 使用新鲜窗口——v0.2 不可机制化，如实披露）。

### major-3：进程内伪造 attestation 可获得有效 seal——Q1 的"绕过必然无 seal 可检测"在此路径为假

**契约**：prereg-gate.md §2 Q1、§6、§7（06 的 `record(trial_id, series, attestation)`）。
**证据**：attestation 是 `_meta` 返回的**无签名普通 dict**（qlib_cn.py:476）。06 落地后，court 级 `record(..., attestation)` 对任何持有 ledger 的调用者开放；agent 在同进程里手搓一条完美 series + 抄一份 conformant attestation 直接 record——链**有效延长**、conformance 全过、harness 自己的 seal 为其背书。Q1 的故事是"(A) 非物理禁止，(B) 使绕过**可检测**（无有效 seal）"——此路径产出的恰是**有效 seal**，(B) 失效。§6 说"self-deception must be deliberate and leaves a reflog"——reflog 只对 git 锚重写成立，对写入时伪造**无任何痕迹**，此句过度声称。
**不改的后果**：07 可能试图用进程内 nonce/HMAC 造假安全（同进程无秘密可言，纯戏剧）。修法：§2/§6 重新框定——seal 证明的是**已记录事件的协议一致性与顺序**，不证明 series/attestation 的**来源真实性**；进程内不可伪造性明确划归 v0.3+ 的进程外分离，并禁止 07 做安全戏剧。

### major-4：§8 只封了 run 合并（N 稀释），run 拆分/run 购物既没被挡也没被披露

**契约**：prereg-gate.md §8、§6。
**证据**：§8 只禁"两个实验塞一个 run"；反向——把一次搜索拆成 10 个 run 各 10 trial，每个内部完全合规、各拿 seal，展示最幸运的那个——无跨 run 登记簿、无机制、无披露。§6 第三条只披露了 run **内**的假设细拆（FDR family 缩小），没披露 run 级拆分；"a new experiment starts a new run"的措辞甚至在邀请它（"experiment"的边界由 agent 自己声明）。叠加 major-1 的无锚窗口，"restart-until-lucky"（弃掉不 seal 的 run）零成本零痕迹。
**修法**：§6 补条 + 规则"出示任一 sealed run 即须出示同一 claim 的全部兄弟 run（RP-1 检查点）"；机制化（跨 run 锚链/run index）可推迟但要点名推迟。

### major-5（10）：最小工人契约的 (c) 条对第二个 CLI 无执行机制——schema 合规今天全靠 grok 的模型级 `--json-schema`，commander 侧零验证

**契约**：dispatch-and-governance.md Part A。
**证据**：`scripts/dispatch.sh:109` 靠 `--json-schema "$(cat "$SCHEMA")"` 在 grok 模型层保证结构；提取段（dispatch.sh:147-178）只检查 `isinstance(receipt, dict)`，**从不对照 `receipt.schema.json` 验证**。换一个没有原生 schema 约束的 CLI，契约 (c) 条"returns a receipt conforming to receipt.schema.json"就是一句无人执行的愿望——`worker_extract_receipt` 会把任意 dict 当 receipt 落盘。另外契约没写"必须可全无头运行"（grok 的 `--permission-mode auto` 埋在缝 1 里，是隐含前提）。
**修法**：两缝重构的 deliverable 里加一行：`worker_extract_receipt` 后接 commander 侧 jsonschema 校验（失败 = 拒收）；工人契约补第 (d) 条"fully non-interactive"。改动极小，但不写进冻结契约工人不会做。

### minor-1（02 §4.1）：`at` 排除在内容哈希外 ⇒ 时间戳可任意改写而链照验——"back-dating"防护声称与机制不符

§1/§6 把 back-dating 列入防御清单、§9 承诺"back-dated series fails"测试，但改 `at`/`registered_at` 不破链（唯一机制载体是 §5 那条自相矛盾的锚条款，见 BLOCKER-1）。物理行序只保**相对**顺序；绝对时间在 seal 前完全无保护。另：排除理由"else honest replay would change the head every run"表述混乱——replay 读的是存储的 `at`，只有**重新执行**才重打时间戳；06 的工人读到这句会误解 replay 语义。保留排除没问题，改写理由、把"backdate 防御"收窄为"reorder 防御"并披露绝对时间不受保护。

### minor-2（02 §4.1）：`type` 是否入 content_hash 有歧义

"content = event minus (at/…, prev_hash, event_hash)" 暗示含 `type`；"stored line = {type, at, ...content, ...}" 的写法暗示不含。若不含，原地翻转事件 type 不破链（多数会在 replay 时因 payload 形状撞上 `LedgerCorruptionError`，但无保证）。一句话定死。顺带：events 里并无 `registered_at` 键（`court/ledger.py` 所有事件 envelope 只有 `at`；`registered_at` 是 replay 派生字段）——"(at/registered_at/…)"是笔误级不严谨。

### minor-3（02 §5）：fail-closed 清单缺条

缺：seal 后任何追加事件 / 第二个 seal → verify 失败（同时封 major-1 的一半）；seal 时**根本不存在**预注册聚合策略（清单只写了"not equal"情形）→ raise；seal 后调用 propose/evaluate → raise；seal 的 `verdict_ids` 未覆盖链上全部 verdict 事件（agent 直调 `court.judge` 在链上留下的野 verdict）→ verify 失败。

### minor-4（02 §4.2）：anchor_ref 入 seal 与 manifest 后置提交存在顺序环

seal 携带 `anchor_ref`，而 manifest（含 `seal_event_hash`）要 git 提交——若锚提交就是 manifest 提交，seal 无法引用晚于自己的东西。前锚（pin chain_head，seal 前）与 manifest 副本（seal 后）是两个 artifact，契约"Git may commit the manifest/anchor once"把它们揉在一句里。补一段精确顺序。

### minor-5（10 Part A）：tripwire 对 `.scratch/dispatch` 全盲被 byte-for-byte 冻结携带

`dispatch.sh:95` 把整个 `.scratch/dispatch` 排除出前后状态比对（并发派单误触发的正当修复，事故 2026-07-10）——副作用：逃逸的工人**恰好改写已提交的审计痕迹**（往期 ticket/receipt，RP-0 的 mechanical traces）不会触发 exit 2。10 裁定"isolation/tripwire/schema stay byte-for-byte"把这个盲点原样冻结且未作为已接受漏洞披露。一句披露即可，或收窄排除模式。

### minor-6（10 Part B）：ticket 10 自身没有 trigger-1 审查存档

`.scratch/dispatch/` 实存 `v02-02-grill / v02-03-grill / v02-power-grill / v01-audit`，**没有任何 v02-10 审查目录**，而 10 的 Status 已是"grilling-locked 2026-07-11"、其正文第一条 trigger 就是"before freezing a design contract → 批给外部模型"。要么本次设计审计就是那个审查（那么"locked"标注早了），要么 trigger-1 在确立它的文档上被跳过——两种都该在文档里记一笔。

### nit（02 §4.1）：float 十六进制编码与 `json.dumps` 的组合需先递归预变换

`json.dumps` 不会为 float 调 `default`，"floats enter the hash via `struct.pack('<d',x).hex()`"必须实现为先遍历树替换 float 再 dumps——可行（Python repr 往返精确，verify 侧重算一致），但给 06 工人写明一句，防止实现成 `default=` 然后困惑。

---

## 已核 ✓ 清单（契约"现状"声称 vs 真库）

- `_append_event` 无 `sort_keys`（court/ledger.py:406）✓
- 每次 append `allow_nan=False` + flush + fsync（ledger.py:406-411）；torn 末行截断+fsync 恢复、中段坏行 `LedgerCorruptionError`（ledger.py:255-303）✓ §4.3 兼容性声称成立
- `register()` 硬编码 `"source_ref": None` 且无参数可达（ledger.py:456）——06 的"source_ref reachability"待补属实 ✓
- `record(trial_id, series)` 今无 attestation 参数 ✓；`judge(ledger, scope, config)` 确接受 caller scope（judge.py:60）✓
- `qlib_cn._meta` 确含 metric/window/universe/data_version/adapter_version/qlib_version/n_evaluation_dates + `meta.config` 全构造字段（qlib_cn.py:476-506）✓
- `DeclaredProtocol` 真字段 = metric/window/periods_per_year/direction/se（ledger.py:45-52 与 spec §5.7 一致）✓（此核对同时暴露 BLOCKER-2）
- dispatch.sh 的 grok 特异性确集中在两缝（CMD 数组 :106-113；structuredOutput 提取 :147-178）；缝外仅 `EFFORT="high"` 默认值等轻微 grok 味 ✓ 大体属实
- "battle-tested 24+ runs"：31 个 raw envelope / 19 个 receipt 实存于 `.scratch/dispatch/` ✓
- `worker-dispatch` / `adversarial-referee` 确已在 `~/.claude/skills/` 全局 ✓
- 10 点名的六个存档目录（meta-review-commander、v01-audit、readme-review、v02-power-grill、v02-03-grill、v02-02-grill）全部实存 ✓
- `worker-bridge.md` 已含 v0.2 ruling 指针段（:97-104）✓；票 02/06/07/09/10 issue 文件实存 ✓

---

## 最锋利的 3 条

1. **BLOCKER-1**：锚"一次于 seal"（§4.3）与"锚不早于 series 则 seal 无效"（§5）不能同真——这是唯一按原文**字面无法实现**的条款，07 落地前必须裁掉一句。
2. **BLOCKER-2**：核心不变量 "attested == declared" 的 declared 侧对 universe/*_version 根本不存在，且没有任何东西把 adapter 配置（label_expr/provider_uri/data tag——即"地面真相的定义"）锁上链——一个 run 级 `run_config` 声明事件同时解决两者，但必须现在写进契约。
3. **major-1+2 合观**：seal 前是无锚窗口（截尾实测零报警）+ 认证路外预筛被官方命名为"legitimate"——**seal 实际证明的远少于 §1 让读者以为的**，而 §6 三条边界一条都没披露这两条最自然的自欺路径。对这个项目，机制缺口可以推迟，披露缺口不行。
