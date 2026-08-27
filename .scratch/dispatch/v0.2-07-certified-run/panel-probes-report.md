# Panel report — 对抗探针镜头（Claude 收货面板，v0.2-07）

**总评：接受工人交付（零工人返工）+ 1 MAJOR 契约层发现 + 2 minor。** 链上所有自欺路径（scope→N/方向翻转/藏 trial/双 policy 排序/post-hoc 夹带）在认证路径全部关死；披露的 §6 边界行为与设计文档一致；诚实账本无一误杀。25+ 不变量探针全绿。**无一 ✗ 归因工人代码偏离票面。**

## Finding A（MAJOR，contract-fault）外锚可被删/清 manifest 静默停用
`anchor_bypass.py` A/B/C 三例全 verify PASS（伪造账本+供真锚后端）：删 run_manifest.json / 置 anchor_ref=null / GitAnchor 版删 manifest——inv 9 门 `if manifest_anchor_ref is not None and anchor is not None`（verify.py:375-378），而 `manifest_anchor_ref` 仅取自本地旁车 run_manifest.json（:294-315），**此文件在重写面内、未入链、未签名、伪造者可删可改**。伪造者全链重写后删 manifest → inv 9 直接跳过 → 即便供了真锚（哪怕锚在受保护远端）也不被咨询。verify 自己独立重算的诚实 final_head **没被用来质询锚**，反用了伪造者能控的 manifest ref。GitAnchor 尤甚（SHA 只存 manifest、删了无从查）。CONTROL（manifest 完整）inv 9 正确拦截——证明机制没坏、坏在触发门与信任源。**归因 contract-fault**：票面 inv 9 原文即"if the manifest carries anchor_ref …"，工人逐字实现，改成 fail-closed 反违契约冻结。工人无过、可胜诉。

## Finding B（minor，contract-fault）verify 接受双 policy 账本（fail-open）
verdict 后插第二个 aggregation_policy declaration + 重封 → verify PASS。`_policy_declaration` 返回首个即停（verify.py:186），无基数检查；而 declare_policy/read_declared_policy 都把 >1 policy 判 corrupt。低严重度（注入需全链重写=A 边界所辖，且 seal 被 inv 5 钉在首个 policy、v0.2 单规则→第二 policy 惰性）。建议 verify 复用唯一性语义。

## Finding C（nit，worker 测试精度 + contract 编号）
纯 legacy 文件实死于 inv 1（缺信封键）非 inv 2；测试正则 `chain` 子串掩盖。

## 探针逐条（预期→实测→判定）
1 诚实基线 verify PASS + CLI exit 0 ✓ / 2 scope：file-drawer✓、野 verdict inv7 死✓、seal 后追加 inv3 死✓ / 3 policy：双 policy **⚠ PASS(Finding B)**、夹带键正反 inv5 死✓、挪位 inv4 死✓ / 4 run_config：挪位 inv4 死✓、att 改 universe/label_expr inv8 死✓、不重叠键改+全链重写 PASS(§6 边界)✓、不重封链断先死✓ / 5 chain_head：seal/manifest 改假 inv6 死✓、manifest anchor_ref 改假 inv9 死✓、**删 manifest ⚠(Finding A 入口)** / 6 完整性：空行/无换行/无信封 inv1 死✓、删 seal "no seal"死+bare open 正常✓、未封删末 eval bare 重放零警告通过（§6 诚实断言）✓ / 7 全链伪造 PASS（§6 预期）✓、供真锚 inv9 死✓ / 8 anchor：文件删/改 inv9 死✓、GitAnchor amend+gc 后 False✓、Noop 恒 True（后门）✓ / 9 misc：judge 中途抛错砖化✓、create 已存在 ValueError✓、open legacy CertificationError✓、混向 court raise✓。

## referee 自评
初轮漏在 reforge 未同步 manifest（旧 manifest 掩盖深层 inv），补测后 Finding A 才浮出。记：**任何 reforge 探针必须同步旁车 manifest 才能测到 inv 6 之后的不变量**。

## 归因汇总
工人：接受、零 fault 返工（唯一 worker 侧 = Finding C 测试正则过松，nit）。契约/指挥侧：Finding A（MAJOR）+ B（minor）系票面 inv 9 / inv 4-5 留洞，工人照做无过。
