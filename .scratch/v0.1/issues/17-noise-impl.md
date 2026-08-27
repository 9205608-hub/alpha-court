# 17 court/noise.py 实现（v0.1-08e）

Type: task
Status: resolved
Assignee: dispatched to grok worker via M0 bridge
Blocked by: 08
Label: wayfinder:task
Worker ticket: ../../dispatch/v0.1-08e-noise-control/ticket.md

## Question

实现噪声对照的法庭侧唯一纯函数 `empirical_null_p`：Phipson-Smyth (2010) 加一修正
p̂=(1+#{null≥观测})/(K+1)，平局对候选不利，永不为零；pass ⟺ p̂≤α（默认 0.05，
参数非常量）。个体陪审团 / 池最大（White 2000）两模式共用同一算术，模式选择在
调用侧。规格 = `docs/design/court-kernel-spec.md` §5.6（rulings F1–F2）；设计契约
与手算向量 = `docs/design/noise-control.md` §4/§8。

- 铁律：本票零生成逻辑——循环时移、偏移网格、RNG 全在 adapter/demo 侧
  （10/11 号票），court 只吃数组。
- TDD：先写 §8 四组向量失败测试（含平局向量与 1/200 分辨率下限），再实现。
- 文件边界：`court/noise.py` + `tests/test_noise.py`。并行。

产出：经验 null 判据可独立计算并逐行对得上文献。

## Answer

grok 工人交付 + 一轮 docstring 返工后收货（2026-07-10，commits `9842789`+`7840183`）。对抗面板双 pass：独立参考实现四向量逐位一致、全护栏路径验证；referee 亲手复核 §8 三向量精确值。13 测试绿。
