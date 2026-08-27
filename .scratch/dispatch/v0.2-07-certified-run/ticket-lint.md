# Ticket-lint report — v0.2-07（派单前对抗性 lint，Claude verifier）

> 结论：修后派，1 BLOCKER + 4 major + 5 minor + 3 nit 全部折入终稿。
> env-AC 按 CR-09 于 base 真跑：ruff PASS、pytest collect 265 干净；CR-09(b) 无未跑消费测试的产物改动（上次 commit 后合并树 248+1 绿）。

- **B-1**：绕过测试二"二次 propose 重声明"不可实现（register 自铸 id，调用方指不到旧 trial）→ 换成可实现三件套：混向 scope E2E raise / 文件里翻 declared.direction 一字节链断 / 同 trial 二次 evaluate raise。
- **M-1**：open() 的已 judge 状态恢复未钉 → 钉死"账本有 verdict = judge 已消费、seal 允许、Judgment 从链上重建；已封/legacy → CertificationError"。
- **M-2**：seal 的 policy 原文取径未钉（read_declared_policy 返回解析对象会洗掉夹带键）→ 钉死取 `DeclarationRecord.payload` 原 dict、禁对象再序列化。
- **M-3**：Anchor 协议四个未定语义 → 钉映射（seal.anchor_ref=ref_before_seal()；manifest.anchor_ref=pin() 返回值；FileAnchor 构造期建锚文件满足"引用物先存在"）。
- **M-4**：judge 半程失败语义 → 钉死 fail-closed 砖化（孤儿 verdict 使 seal 永不可盖，正确结果，入 docstring + 测试）。
- m-1 尾部完整性 crisp 规则（末字节=seal 行后的 \n；空行/缺信封/缺换行全 fail）；m-2 propose 判别 ^h-\d{6}$；m-3 manifest 补 env versions + seal_event_hash≡final head 说破；m-4 补 pre-seal 截尾 assert-passes honesty test + docstring 点名四条 §6 边界；m-5 verify 签名统一。
- n-1/n-2/n-3：GitAnchor tmp 仓 git -c user 配置、git show 措辞、fake evaluator 镜像真 meta 形状。
- 正面核验：全部 code facts 属实；**np.float64 雷真跑排除**（Series/record/JSON/struct.pack 全收 float64）；§5 fail-closed 清单逐条打勾全覆盖；⚠-1/⚠-2 被 verify 不变量 4/5 接住；seal.chain_head"seal 前 head"是唯一可实现读法且与 §4.2 自洽；08 守卫无需重复拦；-m harness.verify 可行；AC 全部可执行。
