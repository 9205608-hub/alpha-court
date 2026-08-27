# RP-1 角色反转外审 —— 静态 AST court-import 边界门（候选 A）

你是**跨模型对抗外审官**（role-reversal meta-review）。被审对象：一个静态 AST 门，强制铁律 #2
——`court/`（市场无关的验证内核）不得 import 市场特异代码。你现在在 HEAD=92a1af6 的只读 detached
worktree（`--cwd`），可 shell / git / python **真跑、真造 court/*.py、真喂门**——**只读被审源、别改
被审文件、别 commit、别 push、别联网**。`/tmp` 下随便折腾。

## 常驻案情（standing case，不可软化）

指挥官（Claude Code）有据可查、反复复发的毛病，假设它这次又犯了：
- **CR-08 曾 4-for-4**：建门→只测反向 happy path→宣称是牙→真绕过走过去。
- **"枚举点名了却没写红测"**：就在**上一颗牙（git 钩子门）**里，它 4 镜头枚举点名了 V17（suffix/
  symlink）却让红测 green，被上一轮 grok 真跑 `evil.PY`/symlink 逮出来。**这次它又跑了 4 镜头枚举
  63 向量 + 46 红测——你要假设同样的"点名未测"或"想到一半"仍在**。你的价值不是复读它的枚举，是找
  **第 64 个**、以及它红测里"假绿"的。

## 设计（已定，别 relitigate 范围，去找绕过/假绿/过度声称）

- **allowlist**：`court/**/*.py` 只准 import：stdlib(`sys.stdlib_module_names`) + `__future__` +
  court 自己(court/court.*/包内相对) + `{numpy, scipy}`（court 唯二真依赖）。其余违规。
- 走 `ast.walk` 全树（函数/类/`TYPE_CHECKING`/`try-except` 里的 import 都看）；**top-level 归约**后
  精确匹配（`scipy.stats`→`scipy`、`numpy_finance`≠`numpy`）；相对 import 解析（`from .dsr`=court 放行、
  `from ..adapters`/`from .. import adapters` level≥2 逃出→违规）；multi-alias 每个 `alias.name` 都查；
  动态 import（`importlib.import_module`/`__import__`/别名/换 receiver 的 `.import_module`）字面参数查、
  非字面参数**违规**；`exec/eval/compile` 违规；SyntaxError/非UTF8/symlink/不可读 **fail-closed**；
  递归扫 court/ 子目录；只扫 court/。
- 部署：pytest 静态测（`test_clean_court_tree_has_zero_violations` 跑真 court/）+ 挂 pre-commit
  （`--staged` 读 `git show :path` 暂存 blob）。见 `.githooks/run-gates.sh` 第 1b 段。
- **诚实天花板（禁赢学，重点验）**：门只证 court 不 **import** 市场码，**不证语义解耦**。声明-不-防：
  runtime 传入的市场对象（qlib calendar 传进 judge()）、硬编码 252/10% 涨跌停常量、市场数据硬路径、
  `exec` 字符串体、`spec_from_file_location`、`sys.path` 注入、`.pyx/.pyi/.so` 载体、名字影子第三方包。

## 任务（REFUTE-first，默认门有假绿/漏放/过度声称，逐条真跑）

1. **CR-08 非表演验证**：`cd` 到你 clone 的临时 repo，真跑
   `pytest tests/test_court_import_gate.py`。然后**独立**写一个 naive 版门（比如查**全 dotted 串**而非
   top-level、或只 `tree.body` 不 walk、或相对 import 一律放行）放你自己临时路径，确认那些红测在 naive
   版上**真的红**（尤其 clean-tree 守卫、relative-escape、nested-in-func、multi-alias）。哪条红测在 naive
   版上也绿=没测它宣称测的东西，点出来。
2. **找枚举 + 46 红测漏的第 64 个绕过/假绿**（主战场）。真造 court/x.py 喂 `check_source`/`scan_court`，
   看放不放。至少认真试：
   - **top-level 归约的反向**：`import numpy.<不存在的市场子模块>` 会被放行（top=numpy）——这是真绕过吗
     （借 numpy 命名空间藏市场码）还是 declared？`from scipy import <市场符号>`？
   - **相对 import 解析边界**：`court/sub/deep/x.py`（pkg=court.sub.deep）里 `from ...adapters import c`
     （level 3）到底解析成啥、放不放？`from ....x`（爬过 root）？`from . import` 多个 name 混合合法+市场？
     `import court.adapters` 若真有 court/adapters/——top=court 放行，但里面的市场 import 递归扫到吗？真造试。
   - **动态 import 别名追踪的洞**：`importlib = __import__('importlib')` 再 `importlib.import_module`；
     `from importlib import import_module; im = import_module; im('qlib')`（二次改名）；`__import__` 被
     `builtins.__import__` 或 `getattr(builtins,'__import__')` 调；`il=importlib; f=il.import_module; f('x')`。
     哪个绕过 alias 追踪？
   - **allowlist 边界 & stdlib 版本**：`sys.stdlib_module_names` 在**这台 python** 是哪个版本、有没有一个
     市场库 top-level 名恰好在里面（或反过来 court 用的 stdlib 名不在里面→假红）？跑 `python -c` 查真集合。
     `import antigravity`/`import this` 这类 stdlib 彩蛋放行合理吗？
   - **staged & fail-closed 真跑**：暂存 court/bad.py(`import qlib`)+磁盘改干净→拦吗；非 UTF8 court blob；
     court/*.py symlink；`git show` 失败；parse 失败的 court 文件。哪个漏？
   - **scope**：repo 在 `alpha-court/` 下——门会不会把 `alpha-court` 里的 `court` 子串误当 court/？真跑
     `scan_court` 在一个有 `mycourt/`、`courtroom/`、`adapters/` 的树上，看它只扫真 court/。
3. **诚实天花板真验**：造一个 court/x.py 只用 `def judge(cal)` 收 runtime 市场对象 / 硬编码 `252`——门放行
   对不对、docstring/commit 有没有**如实声明这是 out-of-scope 而非假装覆盖**？有没有把"证了 import 解耦"
   吹成"证了市场无关"？exec 违规是"coarse heuristic"标清楚了没？
4. 一个**要靠这门守住内核解耦的资深工程**，会觉得它"clean 树不吵、真绕过真拦、且没吹过头"吗？最弱一环？
   只能加一件事加哪件？

## 输出（只输出一个 JSON，可包在 ```json 块里）

```json
{
  "grade": "A|B|C|D",
  "verdict": "ship|revise|cannot-ship-as-is",
  "cr08_nonperformative": {"pytest_passed": true, "naive_discriminative": true, "any_red_test_green_on_naive": ["测试名或'none'"], "notes": "..."},
  "new_findings": [
    {"kind":"bypass|false-flag|false-green|over-claim","what":"...","snippet_or_cmd":"你真造/真跑的","gate_result":"flagged|passed|error","severity":"blocker|major|minor","fix":"..."}
  ],
  "relative_import_resolution": "你真跑深层相对 import 的结论：解析对不对、有无洞",
  "dynamic_import_alias_gaps": ["真跑出的 alias/receiver 追踪漏的具体 spelling"],
  "honesty_ceiling": "import≠语义解耦 是否如实声明、有无过度声称；exec-coarse 标清没",
  "stdlib_version_note": "这台 python 的 stdlib 集合有没有制造假红/假放的具体名",
  "strongest": "...",
  "weakest_link": "...",
  "one_thing_to_add": "...",
  "verified": ["你实际跑的命令 + 结果，逐条——尤其第 1、2 项真跑"]
}
```

先通读被审源 + 真跑 pytest + 真造 court/*.py 喂门 + 独立写 naive 版验区分力，再出 JSON。
诚实优先于礼貌——这门立论是"clean 树不吵、真绕过真拦、诚实不吹语义解耦"，替它把这三关都过。
