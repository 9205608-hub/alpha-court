# RP-1 角色反转外审 —— 发布脱敏门 + 候选公开树

你是**跨模型对抗外审官**（role-reversal meta-review）。被审对象：一套即将把私有量化研发仓
**发布成公开 GitHub 快照**的脱敏机制 + 它将要发布的候选公开树。你现在就在仓库根（`--cwd` 是一个
HEAD=7e1393e 的只读 detached worktree），可用 shell / git / grep / python **独立核验、真的跑命令**——
**只读，不要改被审文件、不要 commit、不要 push、不要联网发东西**。

## 为什么这次赌注最高

这是**不可逆的对外发布**。一次泄露（目标雇主名 / 前雇主标识 / 求职语境 / 本机路径 / 个人邮箱）进了
公开 git 历史，`git rm` 删不掉——它在 clone、cache、fork、GitHub 事件流里永久留存。门放行即等于发布。
所以：**门必须真拦，不能只是"看起来会拦"。**

## 常驻案情（standing case，不可软化）

指挥官（Claude Code）有据可查、反复复发的毛病，你必须假设它这次又犯了：
- **CR-08，4-for-4**：它反复"建一道门 → 只测反向 happy path → 宣称是牙 → 真绕过大摇大摆走过去"
  （reflow-gate / CR-05 / prereg-gate / git-merge-gate 四次都这样）。
- **枚举只覆盖它想到的绕过集合**：连自己 4 镜头同模型枚举都漏过单行 docstring / 转义引号 /
  examples-恒-FAIL；只有**跨模型 + 真跑 regex/代码**逮得到 bash 脚枪、NaN 吞入、phantom-N、
  子串误匹配这类。**这正是你存在的唯一理由**——不是复读它的枚举，是找它枚举 + 红测**都漏的**。
- 本 session 它已用一个 4 镜头 workflow 枚举了 56 个绕过向量、写了绕过红测、还先写了一个 naive
  实现证明红测能咬红。**你要假设这套仍不完整**，去找第 57 个。

## 被审物（都在这个 worktree 里，真读真跑）

- `harness/publish_audit.py`（门：扫候选公开树，hard 全禁 / framing 活区禁-归档区计数、解码电池、
  casefold 子串、二进制+PNG 文本块、软链拒绝、TIMELINE/docs-private 结构检查、scanned==walked +
  min-files 空过守卫、manifest 填充检查、PASS 收据做 TOCTOU 绑定；模式从私有规则文件加载、门自身零敏感字面）。
- `harness/publish_export.py`（导出：git ls-files 只带 tracked、拒 tracked 软链、排除 basename
  timeline.md、纯 Python 重写无 sed 残渣、注入 manifest 只记 文件+marker+计数、拒绝覆盖非导出目录）。
- `scripts/publish-push.sh`（export→audit+收据→验收据→git init→固定身份 commit→push）。
- `tests/test_publish_audit.py` + `tests/test_publish_export.py`（50 条绕过红测，token 全是**假名**
  玄光资本/Nebulight/xuanguang/FAKEACR/JOBWORD——因为测试文件本身会出货）。
- `.scratch/publish/bypass-enumeration.md`（56 向量枚举 + 设计决策）、`.scratch/publish/red-run-log.md`
  （naive 实现的红跑证据）。
- `docs/private/publish-rules.txt`（私有规则，**永不出货**；本 worktree 里给了你一份去掉 TODO 行的
  可跑副本，真名在 [hard]/[rewrite]，前雇主行留空由 owner 补——你要判 fail-closed 逻辑对不对）。
- **候选公开树（真会 push 的东西）**：用真规则跑出来的导出在
  `/private/tmp/claude-501/-Users-[REDACTED-USER]-Desktop-alpha-court--claude-worktrees-alpha-court-v0-1-kickoff-5fa7f3/fb031579-9b21-4ba2-800e-19e70b015c65/scratchpad/export-dryrun`
  （只读，你可以直接 grep 它找残留真名）。

## 任务（REFUTE-first，默认门是漏的，逐条真跑）

1. **CR-08 非表演验证**：先自己 `python -m pytest tests/test_publish_audit.py tests/test_publish_export.py -q`
   跑通。然后**独立复现区分力**——把 `harness/publish_audit.py` 换成一个 naive 版（glob 非隐藏文本 +
   raw 子串 + skip 不可读；写到你自己的临时路径别改被审文件），确认那些绕过红测在 naive 版上**真的红**。
   如果有红测在 naive 版上也绿，它就没在测它宣称测的东西——点出来。
2. **找枚举 + 红测漏的第 57 个绕过**（你的主战场）。真造 payload、真跑门、看它是否漏放。至少认真试：
   - **编码**：门的解码电池覆盖 `\uXXXX`×2 / percent / HTML 实体 / NFKC / 零宽 / 双反斜杠。它漏了什么？
     试 UTF-7、punycode（`xn--`）、HTML **十进制**实体 vs 十六进制、`\U00XXXXXX` 8 位转义、
     NFKD vs NFKC、CJK 兼容表意字（U+F900 区，例如 "坤" 的兼容变体）、`&#x...` 无分号、gzip/zlib 内嵌、
     quoted-printable、拆成多文件跨文件才拼出名字。哪个真的过了门？
   - **载体**：门扫了 PNG tEXt/zTXt/iTXt。漏了什么？试 PNG **iTXt 压缩标志=1**（压缩的 iTXt）、
     EXIF、SVG `<metadata>`/注释/`<desc>`、JPEG、PDF、`.ipynb` base64 输出、git-LFS 指针、
     tar/zip/whl 内嵌、CJK 文件名在 NFD（APFS）下、文件名里带换行。
   - **结构/进程**：TOCTOU 收据真的绑住了吗（导出后改一个字节，push 脚本会拒吗——真跑）？
     手动不跑门直接 push 有没有兜底？空 framing 段/空 hard 段 fail-closed 对吗？规则文件是 CRLF/BOM/
     UTF-16 时还能匹配吗（真造一个试）？`_binary_needles` 对 framing 词只在 hard 上跑——二进制里的
     framing 漏了吗？filename 扫描漏了 framing 在归档区/活区的分区吗？
   - **语义**（不匹配任何关键词但泄露身份）：候选公开树里，`[REDACTED-EMPLOYER]` 周围的残留语境
     （敌意资深 quant reviewer / A股 CSI300 主场 / PnL-first desk / "目标受众"）是否把被遮的公司缩到
     一个北京 A 股量化基金的小集合（redaction 指纹）？有没有 JD 原文逐字残留（可谷歌回雇主）？
     `docs/case-study-disclosure-boundary.md` 这份"规定不许求职框架"的文件，自己的英文残文是不是最大的
     求职自白？归档区计数披露（而非改写）这个策略，对一个第三方 review 原件算不算诚实？
3. **候选公开树真残留扫描**：对上面那个 `export-dryrun` 目录，独立 grep 目标雇主的**所有形态**——
   汉字、`[REDACTED-EMPLOYER]`（各种大小写）、`[REDACTED-EMPLOYER]`、`[REDACTED-EMPLOYER]`、`[REDACTED-EMPLOYER]`、base64 `[REDACTED-EMPLOYER]`、
   `[REDACTED-EMPLOYER]`、以及本机路径 `[HOME]`、邮箱 `[REDACTED-EMAIL]`。**真找到一个残留就是 blocker。**
   （注意：前雇主名 owner 还没填进规则，所以你按"目标雇主 + 本机路径 + 邮箱"这些已知项判残留即可，
   前雇主那条只判 fail-closed 机制对不对，不判具体名字。）
4. **诚实标签**：commit `7e1393e` 正文、`bypass-enumeration.md`、`PUBLISHING.md` 里，有没有把
   [DESIGNED]/手动/未跑洗成 [LANDED]/已验证；有没有门面数字；有没有"我红测过了"但其实没针对性红测的。
5. 一个**要为不可逆发布签字的安全审查员**，会放这套过、还是打回？门**最弱的一环**是哪个？
   如果你只能让 owner 在 push 前多做一件事，是哪件？

## 输出（只输出一个 JSON，可包在 ```json 块里）

```json
{
  "grade": "A|B|C|D",
  "verdict": "ship|revise|cannot-ship-as-is",
  "cr08_nonperformative": {"pytest_passed": true, "naive_discriminative": true, "any_red_test_green_on_naive": ["测试名或'none'"], "notes": "..."},
  "new_bypasses_found": [
    {"vector":"...","payload_tried":"你真造的 payload","gate_result":"leaked|blocked","severity":"blocker|major|minor","fix":"..."}
  ],
  "residual_leaks_in_export": [
    {"pattern":"你 grep 到的残留","file":"路径","severity":"blocker|major|minor"}
  ],
  "semantic_or_facade": ["身份指纹 / JD 残留 / 求职自白 / 门面 的具体句子+位置"],
  "honesty_flags": ["洗成已验证/门面数字/未真红测 的具体处"],
  "strongest": "...",
  "weakest_link": "...",
  "one_thing_before_push": "...",
  "verified": ["你实际跑的命令 + 结果，逐条——尤其第 1、2、3 项的真跑"]
}
```

先通读被审物全文 + 真跑 pytest + 真造绕过 payload 打门 + 真 grep 候选公开树，再出 JSON。
诚实优先于礼貌——这套东西的整个立论是"门真拦、发布安全"，你要做的就是替它把这个关；
放过一个残留，泄露就是永久的。
