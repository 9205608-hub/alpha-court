# 09 qlib-cn 数据可得性研究

Type: research
Status: resolved
Assignee: dispatched to grok worker via M0 bridge (worker ticket: ../../dispatch/v0.1-09-qlib-cn-data/ticket.md)
Label: wayfinder:research

## Question

摸清 qlib 中国社区数据包在本机的真实可用性（含一次冒烟下载验证），产出笔记（asset: `docs/research/qlib-cn-data.md`）：

- 2026 年当前的社区数据获取路径（`qlib.tests.data.GetData` / 社区镜像 / dump_bin 自建），哪条最稳、体积多大、更新到几时
- 数据质量摸底：日频字段（OHLCV/复权因子）、交易日历、csi300/csi500 成分随时间的口径、已知坑（停牌、ST、退市股的表现）
- 本机冒烟：真的下载一份、qlib.init 成功、取一段 csi300 日线并 sanity check（行数、日期范围、NaN 率）
- 结论要回答：v0.1 demo 用哪个宇宙、哪段时间窗、数据够不够干净；"全球可复现"的下载指引怎么写

AFK 票。产出直接喂 [10 adapter 接口与因子评价口径](10-adapter-interface.md)。

## Answer

grok 工人交付（首跑中途 Cancelled，经 `grok --resume` 续跑完成），referee 独立重跑数字后收货（2026-07-10，commit `76ac941`，文档 `docs/research/qlib-cn-data.md`）：

- **关键事实：官方 `GetData` 包停更于 2020-09-25**，对"当前市场"叙事不可用；活路是社区包 **chenditc/investment_data**（README 背书），latest release 2026-07-05。
- 实测（本机）：社区包 813M、下载约 3 分钟；日历 2000-01-04..2026-07-03（6420 交易日）；6114 只标的；csi300 两年面板约 14.5 万行、OHLCV NaN 率约 0.17%。referee 用工人 venv 独立重跑：14.59 万行 / NaN 0.166% / 茅台价格与复权因子正常——一致。
- **v0.1 demo 建议**：社区包 + csi300 + 窗口 2024-07-03→2026-07-03；全新机器复现命令写在文档里。
- 已知坑：macOS arm64 下 qlib 取数需 `kernels=1` + 文件入口（stdin 会撞 multiprocessing spawn）；pyqlib 0.9.7 on Python 3.11.2 可装。
- 交给 10 号票的 open questions：`$adjclose` vs `$close/$factor` 的语义要 adapter 侧单测钉死；是否钉 release tag（如 2026-07-05）换逐位可复现。
- 遗留物：`~/.qlib/qlib_data/cn_data_official_probe`（510M，官方包停更的证据），可删可留。
