# 任务：独立核验 killer-demo 真数据重生成产物（v0.2-08 验收的最后一步）

你是 grok-4.5。v0.2-08（方向感知 battery + verdict role + 判别关聚合）你已交付、
双面板全接受、244+1 全绿合并。收尾一步是 referee 侧的真数据重生成
（`python -m examples.killer_demo`，qlib 全量 ~3h，已跑完并 commit 在 HEAD）。
**你现在独立核验这批产物**——referee 已自验过，你是第二只眼；抓到问题算你赢。

## 工作区（只读，cwd = 本仓库检出）

不要改任何文件。python/git 可用——凡能真跑核验的就真跑。

## 核什么（每条给证据）

1. **头版逐字稳定（确定性承诺）**：`examples/killer_demo/out/report.md` 的头版
   （survivors、accused、|t|、naive p、ICIR）vs 重生成前的版本
   （`git show HEAD~1:examples/killer_demo/out/report.md` 不对——重生成 commit 就是
   HEAD 附近，用 `git log --oneline -- examples/killer_demo/out/report.md` 找上一版，
   diff 两版头版数字）。numpy 2.4.6→2.5.1 跨版本后数字仍逐字相等吗？
2. **账本内部**：`out/ledger.jsonl` 现在是 chained（首事件带 event_hash）吗？
   **真跑 replay**：`court.Ledger.open` 一个副本（copy 到 tmp，别碰原件），链验证过吗？
   verdict roles 分布（应 103 discriminating + 1 informational=dsr）？dsr verdict 的
   `computed` 里有 `dsr` 值吗（v0.1 审计债）？PBO verdict 的 params.metric ==
   "abs_sharpe"？
3. **报告叙事 vs 设计**：battery 表的 Role 列、DSR 行的 abstain 脚注、报告任何地方
   还有没有与 `docs/design/killer-demo.md` §6（v0.2 修订）或
   `docs/design/selection-verdict-isomorphism.md` v2 冲突的旧叙事（五关全票制、
   signed PBO 语句）？
4. **run_config 变化的诚实性**：diff 里只有 numpy/scipy 版本戳吗？有没有该记而没记
   的（比如 policy/aggregation 口径——v0.2-09 才落，现在不该有）？
5. **你自己的 08 代码在真数据上的行为**：有没有任何迹象表明方向机/role/abs_sharpe
   在 100 因子真数据上行为异常（比如 φ 值可疑、role 错标、informational 进了计票——
   头版 0/100 与四判别关叙事一致吗：individual 关 pass 而其它三关 reject 的被告，
   在判别关口径下确实死于 FDR/PBO/pool-max 任一，对吗）？

## 输出

中文。总评（产物可收 / 有问题）+ 逐条证据。刻薄优于空洞；抓到真问题直接点名。
