# 任务：alpha-court v0.1 里程碑技术审计（审产品，不审过程）

你是 grok-4.5。在这个项目里你是主力施工工人，`court/` 内核的大部分代码是你写的。
你之前做过一次"角色反转 meta-review"——那次审的是**指挥官的过程**（票面/裁定/公正性，
打了 B）。**这次不同：审的是产品本身。**

一句话问题：**v0.1 的 `court/` 内核，作为一个"统计法庭引擎"，到底做对了没有、做完了没有、
撑不撑得起宪章说的那个愿景？** 指挥官现在的对外判断是"引擎做完了，但法庭还没上过真案子
（power 从未验证）"——请你用证据支持或推翻这个判断。

## 你的工作区（只读，HEAD=a93b16d，v0.1 完工 + README）

`cwd` 是本仓库只读检出。**不要改任何文件**，读完把审计意见作为文本输出。审计对象：

- **内核** `court/`：`ledger.py`(601) `judge.py`(440) `sharpe.py`(243) `dsr.py`(239)
  `fdr.py`(220) `tstats.py`(171) `pbo.py`(168) `noise.py`(118) `__init__.py`(93)
- **adapter** `adapters/qlib_cn.py`(613)
- **测试** `tests/*.py`（3005 行，11 文件）
- **文献锚** `docs/research/{dsr,pbo-cscv,bhy}.md`
- **设计契约** `docs/design/{court-kernel-spec,trial-ledger,noise-control,adapter-interface,killer-demo}.md`
- **demo 产物** `examples/killer_demo/out/report.md`（真实判决数字）
- `CONTEXT.md`（术语）、`TIMELINE.md`（全程含自省）、`README.md`（对外门面）

## 审计维度（每条要有 file:line 级证据，不许空评）

### 1. 统计正确性（最重——这是引擎的命）
逐个重审四大统计量 + 噪声对照，对照文献笔记与论文原理，找**你自己代码里的错**
（你上次能抓论文勘误，这次抓自己的）：
- `dsr.py`：PSR / E[max SR] / DSR z 路径，ρ̂ 病态外推，单侧性——公式与 `dsr.md` 逐项对得上吗？
  有没有边界（N=1、ρ̂<0、T<½M(M−1)）处理错？
- `pbo.py`：CSCV 组合、λ<0 判据、φ 计算——与 `pbo-cscv.md` 一致吗？S 整除、空矩阵护栏对吗？
- `fdr.py`：BH / BY 程序、c(N) 递归、adjusted-p——你上次赢的那处 min(1,c(N)·P) 现在代码里对吗？
- `tstats.py`：t_iid / t_NW、p 值渐近、SE 语义——NW lags 显式性、极值精度（isf/ppf）修好了吗？
- `noise.py`：Phipson-Smyth 加一 p̂、个体 vs 池最大双模式——公式对吗？
有没有 docstring 声称做了某个缓解、代码其实没做？有没有静默错误路径（本该 raise 却返回垃圾）？

### 2. 架构与解耦
- `court/` 真的零市场特异 import 吗？（子进程断言在 `test_smoke.py`，但设计上有没有暗门？）
- ledger 设计"N 不落盘、按统计量派生"——是干净还是脚枪？append-only / 撕裂恢复稳吗？
- judge 编排：判决极性（统计"发现"⟺ 法庭 pass 的反转）、fail-closed、全参数必传——诚实吗？
- adapter 边界：evaluate/evaluate_shifted 共享内核、qlib oracle 等值——契约兑现了吗？

### 3. 诚实完备性（v0.1 真"做完了"吗）
- "power/二类错误未测"是唯一大缺口，还是有别的半成品接缝？
- 头版跑在**单一预注册种子**上（--sweep 20 种子 ~15h 未跑）——这算不算"证据不足却已收口"？
- 噪声 null 自身的限制（接缝、非风格中性、公共偏移让 p̂ 相关、ρ̂ 病态其实是常态非例外）
  ——这些在 v0.1 是"如实披露的边界"还是"该修没修的洞"？
- 有没有测试覆盖假绿（parametrize 凑数、断言太弱、只测 happy path）？

### 4. 撑不撑得起愿景（v0.2 harness 前瞻）
愿景 = "不会骗自己的挖因子 agent"。v0.1 是引擎。指挥官下一步要做 v0.2 harness
（预注册闸 + 把法庭焊到 idea 生成端 + referee 治理）。
- 现在的 trial-ledger 契约，真的能承载一个预注册闸吗？（declared protocol 锁定、先于序列存在）
- 内核里有没有设计债，到 v0.2 会咬人？（比如 N 派生的口径、judge 的聚合硬编码、
  噪声陪审团不进 FDR 家族这个决策在真实多因子库下还成立吗）
- 从引擎到"能上真案子"，最短的诚实路径是什么？power 怎么才能被真的测出来？

### 5. 最锋利的 3 条
把 v0.1 叫做"v0.2 的地基"之前，你最想先修/先补的 3 件事，越具体越好（file:line + 为什么）。

## 输出要求

中文纯文本。诚实刻薄优于礼貌空洞。先给**总评**（v0.1 court 内核作为地基：稳 / 稳但有保留 /
不稳，一句话理由 + 一个字母评分 A–F），然后按五维逐条给证据化意见，最后是"最锋利的 3 条"。
如果指挥官"引擎做完了"的判断有水分（该说没做完的地方说成做完了），直接点名。
如果你发现自己当年写的代码里有真 bug，如实报——这正是这次审计的价值。
