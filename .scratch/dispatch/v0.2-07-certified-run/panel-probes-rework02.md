# Panel report — 对抗探针（rework-02，v0.2-07；聚焦 106 行 delta）

**接受（ACCEPT）+ 1 LOW 跟进。** 三处新逻辑无绕过无误杀：FIX 1 用 Counter 多重集（非 set，1(b) 重复项蒙混被挡）、court.judge battery:verdict 1:1 故诚实 run 恒不误杀；FIX 2 judgment 位置钉死（前移/后移各被 inv4/inv1 挡）；FIX 3 CLI --anchor 三后端 fail-closed（honest exit0 verified / forged exit1 / none exit0 reported）。§6 全重写边界（删 verdict 造 N=1 自洽伪造）确认仅被锚拦、CLI 无锚可达——既有披露边界非新洞。**LOW（worker-fault，不阻收货）**：畸形 `--anchor file:/dev/null/foo` 抛未捕获 FileExistsError traceback（仍 exit1 fail-closed、验证者自敲、伪造面不可达）；根因 verify.py:550 `except ValueError` 不含 OSError；一行修 → 归 12 号票。误杀检查全 PASS、回归 49/49 + ruff 净。
