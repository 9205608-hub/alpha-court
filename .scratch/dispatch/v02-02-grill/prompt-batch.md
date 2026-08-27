# 批量复审：alpha-court 预注册闸 enforcement 模型（ticket 02，冻结前）

你是 grok-4.5，alpha-court 主力工人。指挥官与用户 grill 完了 ticket 02（预注册闸的
enforcement 模型，v0.2 核心：让用 court 的 agent 无法自欺），Q1–Q5 拍板，写进了设计文档
`docs/design/prereg-gate.md`（DRAFT v1，下方全文贴出）。**派实现票 07 之前**，用户要求把
攒下的存疑项 + "有没有锁错架构" 一次性过你。给真专家意见 + 具体可落地建议，别附和；发现
锁错直接说（上次 power 那轮你就抓出一个把主曲线画在空集上的锁错，这轮同样标准）。

你的 cwd 是只读检出（HEAD）。可核对：`court/ledger.py`（register/record/DeclaredProtocol/
append-only+fsync+撕裂恢复）、`docs/design/trial-ledger.md`（§5 契约、§6/§7 不变量）、
`docs/design/court-kernel-spec.md`（G3 scope 可见排除、§6 fail-closed）、`adapters/qlib_cn.py`
（能不能"背书"metric/window/version）、`docs/design/killer-demo.md`（确定性纪律）。不改文件。

## 已锁定的 Q1–Q5（勿推翻，在此基础上答）

- Q1：(A) 由构造杜绝（harness 拥有 trial 循环、agent 不选 scope、无法"评估而不注册"）+ (B)
  防篡改日志兜底。RP-0：拿掉作弊能力 > 信任意图。
- Q2：court 保持纯（铁律二），`harness/` 当唯一"认证路径"，verdict 带防篡改证书；直接调
  court 仍出 verdict 但未认证。
- Q3：ledger 内哈希链（prev_hash，头哈希=可复算根）+ git-commit-before-series 锚定（RP-0
  已验证模式）。链=完整性，锚=防整体重写。
- Q4 不变量：declared 先于 series / scope=完整注册评估集（harness 派生）/ series↔declared
  conformance（adapter **背书** metric/window/version，harness 校验 背书==declared，背书入链）
  / direction 锁。诚实边界：harness **信任 adapter 背书、不重算 ground truth**。
- Q5：trial 级增量预注册（每 trial 协议先锁 + 无隐藏 trial，非"N 事先钉死"）；agent 只提
  `(hypothesis, declared, spec/params)`，harness 注册→评估背书→record→judge 从完整集派生 scope。
  诚实边界：假设归组锁定可见（RP-1 抓手）但不自动阻止细拆。

## 请你逐条给具体意见（§9 open 项）

1. **防篡改模型**：git-锚 + ledger 内哈希链，是对的吗？"链=完整性、git-锚=防整体重写"这个
   诚实框架站得住，还是 git-锚对 v0.2 过重/过轻？有没有更干净的自包含法（不引 git 硬依赖）？
2. **规范序列化**：哈希要逐字节确定，但 ledger 有**真实时间戳字段**（registered_at 等，设计
   上盖真钟）。哈希该覆盖时间戳吗？（覆盖→确定性与真钟冲突；不覆盖→时间可被事后改而链不破）
   怎么钉最干净？跟 killer-demo 的 byte-identical 纪律怎么接？
3. **conformance 模型**：adapter"背书==declared"够不够？还是 harness 值得抽样重算一小段？
4. **架构锁错**：Q1–Q5 有没有到实现 07 会反咬的锁错？特别是——(A) harness 拥有循环 vs court
   仍接受 caller scope（绕过风险真被证书堵住了吗）；哈希链塞进 append-only JSONL 与现有撕裂
   恢复/fsync 会不会打架；"证书"到底存哪（verdict 里？run manifest？git commit message？）。

## 输出

中文纯文本，诚实刻薄优先。每条给可落地建议，不要"看情况"。最后给一句"能不能冻结派 07"。

---

【prereg-gate.md DRAFT v1 全文】

# Pre-registration gate — design contract (v0.2 ticket 02)

Status: DRAFT v1 (grilling-locked 2026-07-11; pending one batched grok review — §9).
Owner ticket: `.scratch/v0.2/issues/02-prereg-gate-model.md`
Implements into: `.scratch/v0.2/issues/06-ledger-provenance.md`,
`.scratch/v0.2/issues/07-prereg-gate-enforcement.md`,
`.scratch/v0.2/issues/09-aggregation-config.md`

## 1. Purpose & scope

The v0.1 audit's verdict on pre-registration: **the ledger has the seat but not
the gate.** `DeclaredProtocol` can carry a locked protocol and `register` precedes
`record`, but nothing *enforces* that the family the court judges is the full
search the agent actually ran. The court derives the multiplicity N from the
judged **scope**; if the agent controls scope, it controls N — the core self-deception
(under-register / shrink scope to understate multiplicity).

This gate makes the court's own iron discipline **reflexive on the agent that uses
it**. It is the v0.2 embodiment of **RP-0**: a pre-registration must leave a
**trace**, be **re-computable**, and be **tamper-evident** — *only mechanical traces
count, intent does not*. Idea generation stays stubbed (three-don'ts); this gate is
the choke point a future idea-mining agent would pass through so it cannot fool
itself.

## 2. Decisions (grilling Q1–Q5, 2026-07-11)

| # | Decision | Ruling |
|---|---|---|
| Q1 | Enforcement philosophy | **(A) impossible-by-construction** (the harness owns the trial loop; the agent never chooses scope and cannot evaluate without registering) **+ (B) tamper-evident log** as the backstop. RP-0: remove the *ability* to cheat, don't trust intent. |
| Q2 | Placement | **court stays pure** (iron law #2 — a pure calculator, no policy). `harness/` is the **certified path** that owns the loop and derives scope. A verdict is "pre-registration-certified" iff it carries the harness's tamper-evident certificate; a direct `court` call still runs but produces an **un-certified** verdict. |
| Q3 | Tamper-evidence | in-ledger **hash-chain** (each event carries `prev_hash`; the head hash is a re-computable root over the whole run) **+ git-commit-before-series anchoring** (the RP-0 pattern: registration committed before any series exists; git's history is the external anchor against a full rewrite). Chain = integrity; anchor = tamper-proof. VCS-agnostic core, git-commit the default anchor. |
| Q4 | Invariants | (1) declared-before-series; (2) judged scope = complete registered-evaluated set (harness derives, not agent); (3) **series↔declared conformance** — the sanctioned adapter **attests** (metric/window/universe/adapter_version/data_version), the harness checks attested == declared (fail-closed) and puts the attestation in the chain; (4) direction locked before series. |
| Q5 | Granularity & interface | **trial-level incremental** pre-registration (per-trial protocol lock + no-hidden-trials, *not* fixed-N-up-front). Agent proposes `(hypothesis, declared_protocol, spec/params)`; the harness registers (into the chain + git anchor) → evaluates via the adapter (attesting) → records → judges over the complete set. |

## 3. Architecture

- **`court/` unchanged** (except ticket 06's `source_ref` reachability fix). It
  stays a pure calculator + append-only ledger; `judge` still accepts a caller
  scope for pure-function tests and the killer demo's direct use.
- **`harness/` (new)** is the certified path:
  - owns a run object holding the ledger + the running hash-chain head;
  - `propose(hypothesis, declared, spec, params)` → registers (chain + git anchor);
  - `evaluate(handle)` → runs the sanctioned adapter, which returns the series **and
    an attestation**; the harness checks attestation == declared, records both;
  - `judge()` → derives scope from the **complete** registered-evaluated set (the
    agent never passes a scope), runs `court.judge`, and stamps the certificate.
- The agent cannot: evaluate without registering (no eval path outside the loop),
  shrink scope (it does not pass scope), reorder declared-after-series (chain +
  git), or alter the record afterward (hash-chain + git anchor).

## 4. The certificate

A pre-registration certificate = **the hash-chain head + the git anchor ref**
(the commit that fixed the registration before the series existed), stamped into the
run manifest / verdict. Verification (any third party, re-computable): re-hash the
chain from genesis → must match the head; the git anchor must predate the series
commits. A verdict without a valid certificate is **not** a pre-registered result —
this is what gives (A) its teeth (a bypass is detectable, not just discouraged).

Canonical serialization for the chain must be **byte-deterministic** (sorted keys,
fixed float formatting) — the same determinism discipline the ledger already holds
(`killer-demo.md` determinism; §9 review bag).

## 5. Fail-closed semantics (extends court §6)

Every violation is a hard error, never a silent pass:

- a `record` whose trial has no prior `register` in the chain → raise;
- a `judge` scope smaller than the complete registered-evaluated set → raise;
- an adapter attestation not equal to the trial's `declared` → raise;
- a `direction` (or any declared field) changed after the series exists → raise;
- a broken hash-chain or a git anchor that does not predate the series → raise
  (certificate invalid).

## 6. Honest boundaries (禁赢学 — stated on the design's first screen)

The gate defends against a **researcher / agent fooling itself** — changing the
metric/direction after seeing data, shrinking scope, hiding trials, back-dating.
It does **not**:

- **Verify the adapter computed correctly.** The harness *trusts the sanctioned
  adapter's attestation* (attested == declared); it does not re-derive ground truth.
  Correct computation is the adapter's own responsibility (determinism, golden
  fingerprints — `adapter-interface.md`). Do not claim the gate "verifies the data."
- **Prevent fine-grained hypothesis pre-declaration.** An agent may pre-declare one
  economic claim as many narrow hypotheses to shrink each FDR family — the same
  limitation real pre-registration has (you may pre-register many separate studies).
  The gate **locks the grouping before series and makes it visible in the
  tamper-evident chain**, so a reviewer can *see* the grouping choice — but it does
  not auto-prevent it. This is exactly where **RP-1** (external adjudication as a
  heartbeat) is the backstop the gate cannot mechanize.

## 7. Cross-references

- **Ticket 06** implements the ledger side: `register(..., source_ref=...)`
  reachable, and the evaluation event carrying the adapter attestation, cross-checked
  against `declared` at `record` time.
- **Ticket 07** implements the harness gate itself (owns loop, derives scope,
  hash-chain + git anchor, fail-closed).
- **Ticket 09** (aggregation config) is also a pre-registration object: the survival
  aggregation rule (which under ticket 03 counts only `discriminating` gates) must be
  declared and certified before verdicts, not chosen after — same chain, same anchor.
- **Ticket 03** (selection–verdict isomorphism): the gate enforces `direction`
  locked before series; PnL menus must pre-register directional (the 02/03 economic
  seam — the gate is what *makes* that a hard requirement).
- **RP-0 / RP-1** (personal quant-workflow-system): this gate is RP-0 applied to
  alpha-court; the `prereg-gate.sh` "results not before the pre-registration commit"
  pattern is the git-anchor precedent.

## 8. Deliverables (tickets 06 / 07 / 09)

- `harness/` certified path: propose → evaluate(attest) → record(check) → judge
  (derive scope), producing a certificate (hash-chain head + git anchor).
- Hash-chain in the ledger with byte-deterministic canonical serialization; a
  re-computable verification command.
- Tests (red first): the four cheats from §5 each raise; a certified run verifies;
  a tampered ledger / back-dated series fails verification; a scope-shrink attempt
  raises.

## 9. Open items — pending one batched grok review

Before ticket 07 is dispatched, one grok consultation resolves:

1. **Tamper-evidence model** — is a git-anchored in-ledger hash-chain the right
   model, or is there a cleaner self-contained approach? Is "chain = integrity,
   git-anchor = tamper-proof-against-rewrite" the honest framing, or is git-anchoring
   over/under-kill for v0.2?
2. **Canonical serialization** — how to pin the byte-deterministic hashing so it
   composes with the ledger's existing determinism (float formatting, key order,
   the timestamp fields that are "real clock" by design).
3. **Conformance model** — is "attested == declared" a sufficient conformance
   guarantee, or is a cheap sampling-recompute by the harness worth it?
4. **Anything locked wrong** — does Q1–Q5 contain an architectural mistake that will
   bite at ticket 07 (the way the ICIR band bit ticket 01)?

Their resolution folds back here (v2) before ticket 07.
