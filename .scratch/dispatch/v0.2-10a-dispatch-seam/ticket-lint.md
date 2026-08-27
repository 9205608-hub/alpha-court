# Ticket-lint report — v0.2-10a（派单前对抗性 lint，Claude verifier）

> 结论：修后派，2 major + 5 minor + 1 nit 全折入终稿。env-AC 于 base 真跑（bash -n OK / 460 collect / python3 -m ruff 0.15.10 可达）。

- **M1（我的自欺踩线）**：票面把"系统 python3 没有 jsonschema"标为 verified fact——**假**（miniforge base 有 4.26.0，我核错了解释器=venv-merged 非 dispatch 用的 base）。dependency-free 决定本身对（可移植性），但不能挂在假事实上 → 改成真理由（不 *依赖* 可选库、fresh clone/CI/worker 环境未必装）。
- **M2（行为改变陷阱）**：`set +e … "${CMD[@]}" … set -e` 守卫是载荷性的（让 grok 非零退出走优雅分支而非 errexit 死），我只列了裸调用没列守卫 → 补进 must-preserve + 要求 worker_invoke 保留非-errexit 退出码捕获 + GROK_EXIT 块列入不动。
- m3 session 行 §1↔§2 矛盾（extractor 不吐 sessionId 但 §2 说复用其 stdout）→ 删选项 B、钉死 dispatch.sh 用一行 python3 -c 从 $RAW 读。
- m4 校验器构造覆盖不全（漏 deviations/open_questions 的 items.type + files_changed/self_test 的 items-is-object）→ 补进显式覆盖清单。
- m5 behavior-preserving 无 AC 可验只靠裁判读 diff → 要求 receipt notes_for_referee 逐块自证"哪些逐字搬移/哪些改了"。
- m6 AC-5 ruff 三段式（.venv 路径错 + skip 逃逸口）→ 改 `python3 -m ruff` 本机可达必跑。
- m7 blockquote 当逐字引其实是转述 + 偷换 jsonschema→receipt → 标 (paraphrased) + 注明偏离理由。
- n8 worker-bridge.md 已有 3 点契约摘要（缺 d）→ §3 要求收编统一为 a–d 四点。
- 正面核验：seam 定位准、schema 描述逐条对、fixture structuredOutput 真合规且已 committed、TDD/文件所有权/out-of-scope 自洽、.venv gitignore 故 AC-6 不受 worker 造 venv 污染。
