# CR-04 — `| head` SIGPIPE dropped a dispatch receipt

- **root_cause_id**: `pipeline-sigpipe-receipt-loss`
- **attribution**: tooling
- **occurrences**: 1 (expensive+systemic, D3(b): loses the receipt — the whole point of the dispatch — and would recur on any stdout piping)
- **evidence**: TIMELINE 2026-07-10 "court/ 内核完工" ("`| head` 截断 dispatch stdout 会 SIGPIPE 掉收据落盘")
- **fix**: `scripts/dispatch.sh:25` `trap '' PIPE` added this session; receipts already persist to files (`RAW`/`RECEIPT`), so a downstream `| head` can no longer kill the script before persistence
- **anti-recurrence**: re-runnable — `grep -q "trap '' PIPE" scripts/dispatch.sh`; and `dispatch.sh ... | head -1` no longer prevents the receipt file from being written
- **polluted-rework**: none
