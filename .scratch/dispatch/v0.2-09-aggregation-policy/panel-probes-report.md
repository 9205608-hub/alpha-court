# Panel report — 对抗探针镜头（Claude 收货面板，v0.2-09）

**总评：接受。** 49 脚本化探针 + 3 微探针全真跑，零 ✗；无 fail-open/误杀。两条 ⚠ = 票面明文划定的设计边界，转 07 交接注记（已写入 07 票面）。

- 构造攻击 24 例全 ValueError ✓；排序守卫（fresh 放行/verdict 后 raise/二次 declare raise）✓；双 policy read raise + 异 kind 忽略 + 垃圾 payload fail-closed ✓；apply bypass raise + 鸭子对象 raise ✓；10 fixture case 与 HEAD~1 旧实现 oracle 级双向等价（含 gates_faced_passed）✓；identity 5/5 ✓；52 passed 40min 全文件真跑 ✓；链交互（chained 前进/合成 legacy 照常/sealed 被拦）✓；e2e declare→judge→read→apply 三方一致 ✓。
- **⚠-1（07 硬注记）**：verdict 后直接 append_declaration 可塞后补 policy 且 read 视为合法；DeclarationRecord 不暴露链上交错顺序——07 seal 复核必须查**链序**（policy 事件序位 < 首 verdict 序位），只查存在性会被穿过。
- **⚠-2（07 注记）**：from_payload 静默丢弃未知键——夹带键对对象级比较隐身；seal 核对须钉死在账 payload 原始 dict 级相等（或改拒未知键）。
- Note-3（nit → 12）：params 按引用存储可绕构造期不变量（to_payload 硬编码 {}，实害≈0）。
- 归因：worker-fault 无 / contract-fault 无实质项 / referee-fault 无。
