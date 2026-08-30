<!-- capsule-v2 -->
# Daemon activation guard — how do you make install/uninstall wait for (or refuse) live sessions without killing them?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What is the injectable ops contract for binary mutation, and how do BUSY vs REFUSED differ on the wire?

## Ops vtable {reserve, release, diagnose} + BUSY-means-close-sessions message
**Path/Symbol:** `src/daemon/version_cohort.h:80–95` (`cbm_version_cohort_reserve_for_mutation`) + tests/test_version_cohort.c:309–443; engine src/cli/cli.c:255–295.
**Signature:** `cbm_private_file_lock_status_t cbm_version_cohort_reserve_for_mutation(manager, deadline_ms, quiesce_fn, ctx, quiesce_result_out, lease_out);` — CLI wraps via `cbm_cli_activation_guard_with_ops(const cbm_cli_activation_ops_t *ops, mutation_fn, ctx)`.
**Data Shape:** Ops vtable: reserve_for_mutation(context, &lease) → 1=granted / 0=BUSY / other=refused; mutation_lease_release; visible_diagnostic. Reserve failure ⇒ typed message: BUSY ⇒ "real sessions hold it — closing them is the remedy"; anything else ⇒ "NOT a running-session problem — the check that refused was: <detail>" (#1537).

### Decisive source
```c
/* 0 means the cohort was BUSY: real sessions hold it and closing them
 * is the remedy. Anything else is the reservation itself failing, and
 * telling that reader to close sessions sends them after processes that
 * do not exist (#1537). */
cli_activation_diagnostic(ops, reserve_status == 0 ? CLI_ACTIVATION_BUSY_MESSAGE
                                                   : CLI_ACTIVATION_REFUSED_MESSAGE);
```

**Flow:** CLI mutation entry → production context init (or injected test ops) → reserve cohort for mutation → BUSY ⇒ actionable close-sessions diagnostic, refused ⇒ check-name diagnostic → granted ⇒ run mutation under lease → release in all paths; partial failures keep binaries intact (see activation-transaction capsule).
**Invariant:** Diagnostic text must distinguish WHO can fix the problem; a failed reservation must never strand a lease.
**Probe:** `tests/test_cli.c` activation refusal/diagnostic family (e.g., `cli_activation_refusal_note_reaches_diagnostic_issue1416`) plus version_cohort mutation family.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_cli_activation_guard_with_ops", limit: 5 });
```

## Verdict
Adopt ops-vtable injection + cause-specific diagnostics for destructive maintenance gates; adapt messages; the #1537 lesson — match remediation advice to failure class — generalizes everywhere.
