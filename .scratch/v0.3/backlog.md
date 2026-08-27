# v0.3 交接清单（2026-07-31，随 v0.2 验收留档）

> 宪章路线：v0.3 = 刀片库（gates/ 便宜刀模块化）+ null 博物馆成型。
> 本清单 = 宪章项 + v0.2 验收/整改沉淀的顺延项。

## 宪章主线

1. **gates/ 刀片库**（当前为空包占位）：恒等式退化检查、池内冗余 ρ、
   量级 vs 换手、单年运气热力图（宪章 §架构）。
2. **null 博物馆成型**：null 归档从 morgue 表升级为可浏览的档案面
   （与"禁赢学：null 与幸存者同权"逐条对齐）。
3. **真实市场因子上案**：第一单非构造信号的真实因子过庭（连通
   factor-research-flow 上游纪律）。

## v0.2 顺延（评估过、有意后置，防静默丢弃）

4. **grok RP-1 跨模型审查 ticket 12**（`610f9f82`）——配额恢复即做，
   须在下一轮快照发布前完成（issue 12 Answer 载明）。
5. **harness/__init__ 惰性导出**（PEP 562）：eager import court.judge 使
   `-m harness.*` 依赖 cwd 可解析 court；真实调用不受影响、`-P` 绕过在位，
   认证路径包初始化重构单独立项（issue 12 记录性裁定）。
6. **killer demo 报告点名幸存规则**：报告正文未写"survivor = 全部判别关
   unanimous pass"（规则在 killer-demo.md §6 + aggregate.py 显式）。一句话
   改 report.py，随下次产物重生成一并落（避免纯措辞改动引发全账本时间戳
   churn）——v0.2 验收 LOW observation。
7. **演示录屏嵌 README**：`killer-demo.svg`（termtosvg 真录 + 空闲压缩）
   已产出，owner 验收后决定嵌入位置与是否随快照发布。

## 关联项目（不入本仓）

8. **spencer-quant ↔ court 交叉验证测试**：两套 DSR/PBO 原生实现同序列
   互证（容差级断言），重复实现从漂移隐患变互审证据。落在 spencer-quant
   仓，单独立项。
