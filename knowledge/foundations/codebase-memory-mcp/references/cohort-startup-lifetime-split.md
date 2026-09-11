<!-- capsule-v2 -->
# Version cohort lifetime lock — why does the daemon startup lock get its own file from the cohort lifetime?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What breaks if you reuse one lock file for both "daemon is starting" and "build X owns the account"?

## Distinct stable files; startup lock never repurposed
**Path/Symbol:** `tests/test_version_cohort.c:519–540` (`version_cohort_does_not_repurpose_daemon_startup_lock_for_lifetime`) + `src/daemon/version_cohort.c` manager construction.
**Signature:** manager created per endpoint (`cbm_version_cohort_manager_new(endpoint)`), meeting at stable native lock files distinct from the daemon startup mutex.
**Data Shape:** Startup transition lock: held only during daemon bootstrap. Cohort lifetime SH/EX: held for the process lifetime by every admitted participant. Maintenance gate: EX during install/update/uninstall.

### Decisive source
```c
TEST(version_cohort_does_not_repurpose_daemon_startup_lock_for_lifetime) { ... }
/* Managers independently reopen no paths: the endpoint duplicates its
 * already-validated owner-only runtime-directory handle. All managers for one
 * account therefore meet at the same stable native lock files. */
```

**Flow:** endpoint handle duplicated (no path reopening) → managers derive the SAME stable lock names account-wide → startup uses its short-lived lock → participants hold lifetime SH → activation takes EX → maintenance takes intent+admission EX.
**Invariant:** One lock, one meaning — overloading startup and lifetime semantics creates races where a restarting daemon drops everyone's admission or blocks installs forever.
**Probe:** `tests/test_version_cohort.c:version_cohort_does_not_repurpose_daemon_startup_lock_for_lifetime` plus `version_cohort_exclusive_activation_blocks_and_is_blocked_by_participants`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "version_cohort_manager_new", limit: 5 });
```

## Verdict
Adopt purpose-per-lock-file discipline for multi-role coordination; adapt naming; the duplicate-don't-reopen runtime-dir rule closes fd-lifetime bugs.
