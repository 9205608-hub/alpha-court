# Ticket-lint report — v0.2-09（派单前对抗性 lint，Claude verifier）

> 结论：修后派，7 处已折入终稿。env-AC 按 CR-09 于 base 真跑（ruff PASS / pytest collect 干净）。

- **M1**：票面事实列了 main 分支才有的 publish_audit/publish_export（幽灵模块，本分支 harness 只有三个 session-governance 模块）→ 改为实际清单。
- **M2**：tracked `alpha_court.egg-info/` 被指挥官 .venv-regen 弄脏——工人 AC-1 安装必重生成、`git add -A` 必超边界挂 AC-5 → 指挥官在重生成 commit 一并提交刷新的 egg-info + 票面加 "checkout -- egg-info" 指引。
- m1：import 面补第五个调用点（test_judge_direction.py）。
- m2：`aggregate_sweep_rows` 钉死留 demo（sweep 行 dict 非 verdict 形状——答案唯一不外包给工人）。
- m3：unknown-rule 测试删 from_payload tampering 死路（只留 dataclass bypass）。
- m4：thin re-export 需 `__all__`（ruff F401）。
- n1/n2：declare_policy 不查链模式（07 的 seal 侧管）+ 返回值=declaration id。
- 正面核验：prereg-gate 引文逐字准（or-branch 未砍、07 兼容）；Ledger API 全对；identity 测试与 re-export 写法兼容且自我强制；test_smoke 方向不咬 harness→court；issue 冲突已被其审计修订节自解；run_config 现不记 policy、输出冻结无矛盾。
