# Panel report — 对抗探针（rework-01，v0.2-07）

**接受工人交付、两目标 fail-open 真关闭、无新洞无误杀。** FIX 1（judgment 上链堵 reopen 复活）+ FIX 2（锚 query-by-recomputed-head fail-closed）+ FIX 3（一 policy 不变量）全生效，25+ 探针全绿。抓出 1 major 契约层残洞 → Finding 1（judgment.battery 上链但从不交叉核、CLI 恒 anchor=None 抬进可达面）+ 2 minor（judgment 位置不校验、CLI 无锚入口）。全部 contract-fault，工人可全胜诉。详见 referee-repro-battery.py（Finding 1 亲证）→ rework-02。
