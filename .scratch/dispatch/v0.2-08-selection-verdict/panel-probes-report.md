# Panel report — 独立复算/对抗探针镜头（Claude 收货面板，v0.2-08）

**总评：接受。** 八探针全真跑：0 ✗、1 ⚠（replay 侧 role 值域不校验——方向性安全，垃圾值落入更严的 discriminating 分支，无 candidate-favorable 通道；归轻 contract-fault，一行工作量并入后续票）。数值层零错配。

## 探针结果
1. abs/neg 复算：自建混号矩阵（三形式 φ 0.10/0.05/0.00 两两不同，探针不可能空转）→ judge 三 declared 的 φ 与独立重写的 CSCV **逐位相等**；params.metric 逐一对；φ 翻转 1/3→2/3 复现 ✓
2. DSR 三分支：greater(X) 与 less(−X) computed **精确相等**（==）；two-sided informational 且与 greater 同数据逐键相等；ρ̂ 取负不变独立复算 ✓
3. role 攻击：nonsense→ValueError 零部分写入；None 不落键；合法链注入 informational→replay 读出；未重封链篡改被拒；**合法链注入 "banana"→replay 照单全收** ⚠
4. 聚合攻击：4 disc pass + info reject → True；info pass + disc reject → False；全 informational → False（no free pass 兑现）；None reject → 杀；无属性 stub → discriminating ✓
5. 混向 raise：双向/三向报文含全部方向名；混向账本单 trial scope 的 individual 门不误伤 ✓
6. 端到端小 demo 真跑（298s）：DSR informational、PBO abs_sharpe、0 幸存与判别关重算一致；Role 列/abstain 脚注/新措辞在；旧假话 0 hit；morgue /4 ✓
7. 回归嗅探：旧 test_judge.py 对新代码 13/14 过、唯一红恰是被迫红的 pbo 测试（"数值不变"声称成立）；G2 极性全过 ✓
8. legacy：out/ledger.jsonl 副本 104 verdicts、role 全 None、新聚合仍 0/100、faced=5（None=discriminating 兑现）✓

回归底账：非 demo 227+1 exit 0；killer_demo 12 passed；judge+direction+ledger 54 passed；ruff 0；边界零越界。

## 归因建议
无 worker-fault；唯一 ⚠ 归轻 contract-fault（replay 侧是票面没写死的缝）。结论：接受。
