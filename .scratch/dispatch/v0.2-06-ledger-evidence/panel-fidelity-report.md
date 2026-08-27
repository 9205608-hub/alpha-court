# Panel report — 契约保真镜头（Claude 收货面板，v0.2-06）

> 独立复跑确认：全套件 219 passed, 1 skipped（与 receipt 逐字吻合）；ruff 30 错全 confined 在 `.scratch/dispatch/v02-design-audit/referee-verify*.py`（指挥侧 BASE 就有）。

**总评：返工（小修）** — canonical 哈希路径一处真实缺陷（合法输入的非 str 键 dict 写入成功、重开假阳性 `LedgerCorruptionError`）；其余逐条全对上，receipt 无静默偏离。

## Findings

### major-1（临界 blocker）：canonical_json 对非字符串 dict 键不设防 → 假阳性 corruption / 裸 TypeError
- 票面 §3 只钉了 float 值预变换（自问自答 bool/int/NaN 值型），对键型缄默 + 硬约束 4 fail-closed。
- 实现：`court/ledger.py:158-171`（只变换值）、`:174-182`（sort_keys）、`:150-155`（serializable 检查放行非 str 键）。
- 实证 A：`register(hid, {"nested": {2:"x", 10:"y"}}, …)` 写入成功（int 键数值排序入哈希）；重开 json.loads 还原 str 键、字典序不同 → `LedgerCorruptionError: event_hash mismatch`。诚实账本自证"被篡改"。
- 实证 B：混合键 `{1:"a","b":2}` → 裸 TypeError 逃出（应 ValueError）。无部分写入、内存链头未推进。
- 归因建议：contract-fault 为主 + worker-fault 次之。修复：pre-transform 遇非 str 键 raise ValueError。

### minor-2：source_ref 无运行时类型守卫（传 dict 静默存储；与既有 statement 风格一致，报备）
### minor-3：test_flip_type_raises 不唯一证明链抓 type 翻转（schema 崩也绿；实现本身正确，测试证明力弱）
### nit-4：mixed-file 测试只测 hashless→hashed 一向（反向实现有抓、面板实证过，套件未覆盖）
### nit-5：_append_event 写盘前推进内存链头（`ledger.py:638` 先于 write；超票面范围，记录在案）
### nit-6：attestation/payload/spec 按引用存储（与 v0.1 spec/params 先例一致，不算偏离）

## Receipt 交叉核验：无静默偏离
- AC-4 deviation 属实（30 错全在指挥侧脚本，owned 三文件 ruff 绿）= contract/environment-fault。
- 全套件独立复跑 219+1；diff 只碰两文件；test_ledger.py 零改动；killer-demo 账本未动；court/__init__.py 未动（所有权正确——代价：DeclarationRecord/SealRecord 无包级导出，07 的 seam，指挥侧记账）。
- 31 个新测试（≥18 ✓）；TDD red = exit 2 collection ImportError，合 AC-6 字面。

## 逐条已核 ✓（9 组）
1. §1 source_ref ✓（签名/落盘/replay/round-trip；仅 minor-2）
2. §2 attestation ✓（全部检查 + 双错误路径：写 ValueError、replay 包 LedgerCorruptionError `:531-542`，chained+legacy 两形态实证；None 合法且省键、旧式行字节兼容）
3. §3 哈希链 ✗ 非 str 键（major-1）；其余 ✓（content 定义/公式逐字/genesis/float 预变换 bool 免疫/先算后写再 fsync/存储行冻结/unicode+极端 float round-trip 实证）
4. chain_head ✓（空 chained=genesis、legacy=None、信号不重叠）
5. replay 校验 ✓（六类篡改全抓；torn 尾行 truncate + 续链正确；honesty test 真实存在、指向 prereg-gate §6、真断言通过）
6. §4 legacy ✓（判定在截断后；killer-demo replay ✓；legacy 续 append 无哈希；混合双向都抓——一向测试、反向实证）
7. §5 declaration/seal ✓（六 mutating 入口 `_require_not_sealed` 均首检；seal-final replay `:475-478`；seal 后 torn=truncate；事件行键形合票面；ID 扫描一致）
8. 既有行为回归 ✓（test_ledger.py 零 diff、25 基线绿、fsync 原样、全套件 219+1）
9. 过度实现 ✓ 基本无（canonical_json 等公开函数：07 要用，建议 07 契约认领；无顺手重构、无票外功能）

**建议处置**：major-1 一处返修（键守卫 + 双向测试连 nit-4 顺手带上），复验后可收。工人申报纪律干净。
