# Ticket-lint report — v0.2-08（派单前对抗性 lint，Claude verifier；env-AC 已按 CR-09 真跑于 base）

> 结论：修后派。1 BLOCKER + 1 major + 3 minor + 3 nit，全部已折入票面终稿；两处文档过期由指挥官派单前修入 base（killer-demo.md §5.4 PBO bullet + §6 "0/5" 例）。
> env-AC 真跑：`ruff check .` 于 base PASS；`pytest --collect-only` 227 tests 干净收集。

- **BLOCKER-1**：`tests/test_judge.py::test_pbo_cscv_pass_and_reject`（two-sided fixture + 带符号 oracle）在 abs 形式下 φ 1/3→2/3（lint 亲跑），砸中票面禁改的 decision 断言——票面内部矛盾，工人无路可走 → 票面显式授权把该测试/fixture 的 declared 改 `greater`、断言逐字节不动、入 deviations；two-sided abs 覆盖放 test_judge_direction.py。
- **major-2**：`report.py:219-224` footnote "PBO's internal selection is signed…" 改后为假话，且同源 killer-demo.md §5.4 对工人冻结 → Task 4 加 footnote 替换（03 §4 process 措辞）；文档由指挥官先修。
- **minor-3**：aggregate 读 role 必须 `getattr(v,'role',None)`（现有测试 SimpleNamespace 无 role 属性）→ 已写入。
- **minor-4**：ledger role round-trip 测试落点未点名（新建 test_ledger_role.py 会违反 AC-5）→ 点名住 test_judge_direction.py。
- **minor-5**：`gates_faced_passed` 只数 discriminating 与 killer-demo.md §6 旧例 "0/5" 对不上——裁定票面对、文档例子过期 → 指挥官修文档（被告 x/4）。
- **nit-6**：'"five gates" phrasing' 是空集 → 改点名 report.py:148 docstring + battery Role 列。
- **nit-7**：registry 校验顺序留实现自由度（可共存，无矛盾）——放行。
- **nit-8**：禁 bump `court.__version__`（test_judge.py:670 钉死）→ 已写入。
- 正面核验：current code facts 全部属实（行号 ±1 漂移）；`append_verdict` 加默认参不咬 test_ledger*（无事件键集合精确断言；role=None 不落盘、legacy 复制测试字节安全）；小 demo 无幸存者数绝对断言（"DSR 独杀翻计数"风险不成立）；混合方向 guard 不咬现有测试；less 分支在 `_apply_dsr` 数据流落得下（负号不变量成立）；AC 全部可执行。
