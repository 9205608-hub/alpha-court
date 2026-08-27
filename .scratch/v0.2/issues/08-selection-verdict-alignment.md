# 08 选择–判决对齐实现

Type: task
Status: resolved
Triage: done
Blocked by: 03
Label: wayfinder:task

## Question

按 03 拍板落地"扫描规则 ≡ 统计原假设"的解法，消灭"空转关参与全票制叙事"。

- 按 03 选定的路径实现其一（或组合）：对齐裸选口径 / DSR 仅在预注册 directional 假设下
   启用 / battery 逐关申报适用性 + 聚合只对判别关计票。
- 回写 `docs/design/court-kernel-spec.md`（判决极性表 / battery 配置）与——若 03 改了
   demo 口径——`killer-demo.md` 与 killer-demo 产物（注意 ledger schema 若变，committed
   `examples/killer_demo/out/` 需按 11 号验收重生成）。
- 与 07 的 direction 锁在"闸侧 vs 统计侧"分工上不得冲突（03 已划界）。
- TDD 红绿：先写"弱关被当判别关计入幸存"的失败断言，再按新协议转绿。

## 验收标准

- referee 独立复核：DSR/PBO 在其不适用的语境下不再被当作判别性证据计票（按 03 口径）。
- spec/demo 文档与代码逐项对齐；相关测试零回归；ruff 净。

## 审计修订（2026-07-12，v0.2 设计层审计 D4/D5/D16 — 冲突处以本节为准）

- **role 落点已裁定**（03 v2 §4）：`VerdictRecord` 新增可选字段 `role: str | None =
  None`（对齐 `engine_version` 先例），旧账本 replay 兼容（None = pre-v0.2）。
- **`less` 分支**按 03 v2 Q2 表：PBO metric = 负号形式（`-sharpe`/`-ICIR`）、DSR =
  翻转序列重算矩后跑原版；**混合方向 scope → raise**（家族级闸无原则性单分支）。
  invariant 测试三分支全覆盖。
- 03 §3 论证已重写（一真地雷 + 引用铁律；两条 v1 地雷已 retired 在案）——08 的
  docstring/注释引用以 03 v2 为准，不得复述已 retired 的论证。
- killer-demo 重生成为**唯一一次**（09 不再重生成）；顺序按 map 冲突矩阵 06 → 08 → 09。

## Answer（2026-07-13 收货，referee 终裁）

**已交付并收货，零返工**：dispatch `v0.2-08`（工人 grok，单轮 `722c63a`）。9 文件 +854：
verdict `role` 可选字段（None 不落键、旧账本字节不变）、judge 方向机（同质守卫 + 三分支
+ role 派生 + G5 registry abs/neg 形式、params 记解析名、前缀拒绝 caller 越权）、demo
聚合判别关化 + 叙事四关化、`__init__` 补 06 seam 导出。

**收货强度**：裁判全量 244+1 绿（28 min 含全部 demo E2E）+ 双面板全接受——契约保真
零 findings（8 组逐条 ✓，红测被独立证实结构性红）；复算探针 PBO 三形式 φ 与独立重写
CSCV **逐位相等**、DSR less(X)==greater(−X) 精确相等、小 demo 真跑 298s 验证叙事、
legacy 0/100 保持。

**归因入账**：零 worker-fault；唯一 ⚠（replay 侧 role 值域不校验——方向性安全）=
轻 contract-fault（票面只钉 append 侧），已入 12 号票批处理；4 nit（收据记账/测试
match 判别力/死代码/微效率）同入 12。预授权 deviation（`_aligned_three_trials` 改
greater）如实申报、断言字节不动、数值不变性面板证实——**派前 lint 抓 BLOCKER 的价值
实证**（不抓则工人两头违约必返工）。

**遗留（referee 侧验收步骤）**：killer-demo 真数据重生成（~1h qlib 任务，清 committed
ledger.jsonl 落后字段之债 + 落新 role/abs_sharpe 产物）——合并后由指挥侧执行并单独
commit，出处注记本 Answer。

### 重生成验收补记（2026-07-13）

真数据重生成完成并经 grok 第二只眼独立核验（`.scratch/dispatch/v0.2-08-selection-verdict/
regen-review-report.md`，判"产物可收"）：头版选择统计字节级稳定（100 series SHA-256 零
失配、t 向量 bit-identical，跨 numpy 2.4.6→2.5.1 + scipy 1.17→1.18 + **python 3.11→3.12**）；
账本 404 事件全链、replay+篡改检测真跑通过、DSR 路径数值与旧版 bit 级一致仅多落 `dsr≈1.14e-7`；
PBO φ 0.5197（abs）vs 旧 signed 0.4731 皆贴噪声中心。3 nit 入账：① p 向量 54×1-ULP
尘埃——确定性承诺措辞应为"头版与可见位稳定"非"全 float bit-stable"；② `run_config.gate_verdicts`
摘要层仍扁平五关无 role（report/ledger 已正确）；③ morgue `φ` 列名（AR1 参数）与 PBO φ
撞名（预存命名债）。①②可并 09/12 收尾顺手清。
