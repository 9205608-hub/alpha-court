# 11 v0.2 E2E 验收

Type: task
Status: resolved (2026-07-31 referee 亲执通过 — 见 ../acceptance-report.md)
Triage: ready-for-human
Blocked by: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10
Label: wayfinder:task

## Question

v0.2 收官闸门（referee 亲执，延续 v0.1 12 号票的尺度）：

- **法庭上过真案**：power 标定（05）一条命令跑通，**size 表与 power 表并列**呈现；
   法庭在已知构造信号上展现判别力（power 随强度上升），size 仍校准。
- **预注册闸挡得住自欺**：referee 亲跑三条绕过路径（scope 缩水 / post-hoc 翻号 / 篡改
   痕迹）全部 fail-closed（07）；证据链（06）可 replay 还原。
- **选择–判决同构**：弱关不再被当判别关计入幸存（08）；聚合口径显式、先于判决落盘（09）。
- **解耦守卫升级**：白名单守卫抓得住 court 的白名单外 import（04）。
- **诚实条款逐条**：power 难看也如实报（禁赢学）；size≠power 分表；构造信号≠真实 alpha
   边界写清；null/失败归档与成功同权。
- **铁律逐条**：court/ 零市场特异（白名单守卫）；统计实现文献引用齐；ledger schema 若变，
   committed demo 产物已重生成、确定性逐位复算成立。
- **交接**：v0.3（gates/ 刀片库、null 博物馆、真实市场因子上案）待办清单留档。

## 产出

验收报告。通过 = v0.2 完成，map 关闭。

## Answer（2026-07-31）

验收通过（PASS + 1 LOW observation + 1 发布前提），报告全文
`.scratch/v0.2/acceptance-report.md`。要点：at-HEAD（610f9f82）真数据 E2E
逐位复现（404 事件唯一差异字段=at）；referee 独立 8 探针 8/8 fail-closed
（scope 缩水/post-hoc 翻号/篡改 + replay）；role 面板零缺失、认证路径
policy 先于判决开链；诚实条款与铁律逐条核过。LOW：demo 报告正文未点名
幸存规则 → v0.3 backlog #6。发布前提：ticket 12 grok RP-1（配额恢复后、
快照发布前）。**v0.2 完成，map 关闭。**
