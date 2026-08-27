# 新鲜上下文对抗审阅 —— worker-dispatch / adversarial-referee 改 DeepSeek 版（2026-08-15）

被审：指挥官对 `.claude/skills/worker-dispatch/SKILL.md`、`.claude/skills/adversarial-referee/SKILL.md`、
`scripts/ticket-template.md` 的改动（diff 见 commit 前的工作树；改动动机=HQ 2026-08-15 AI 协作全流程审计）。
审阅官：同厂商（Claude）新鲜上下文子代理，无主 session 先验；**跨厂商（dsh）复审待补**。
任务：A 事实核对（skill 对 dispatch.sh/resume-worker.sh/dsh 行为的每句描述能否在脚本里找到依据）；
B 内部矛盾/过度声称；C 绕过/假绿；D 对工人不公平之处。REFUTE-first，输出 JSON 判决。
