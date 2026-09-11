<!-- capsule-v2 -->
# Diagnostics output safety — how do you write crash diagnostics without symlink attacks or wedged shutdowns?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What defenses protect predictable /tmp diagnostic paths, and how do you bound the periodic writer?

## Symlink rejection + owner-private files + interruptible periodic wait
**Path/Symbol:** `tests/test_diagnostics.c:diagnostics_rejects_predictable_tmp_symlinks` (119–160), `diagnostics_outputs_are_owner_private_regular_files` (220), `diagnostics_stop_interrupts_periodic_wait` (183); engine src/foundation/diagnostics.c.
**Signature:** `bool cbm_diag_start(void);` writing snapshot JSON + trajectory NDJSON under tmpdir with pid-derived names.
**Data Shape:** Pre-existing symlink at a diagnostic path ⇒ refuse to follow/write; outputs must be REGULAR files with owner-only perms; the periodic writer's sleep must be interruptible by stop so shutdown never waits out an interval.

### Decisive source
```c
TEST(diagnostics_rejects_predictable_tmp_symlinks) {
    ... symlink(snapshot_target, snapshot_link) ...
    ASSERT_EQ(cbm_setenv("CBM_DIAGNOSTICS", "1", 1), 0);
    ASSERT_TRUE(cbm_diag_start());
    ... /* must not clobber through the link */
}
TEST(diagnostics_stop_interrupts_periodic_wait) { ... }
```

**Flow:** start → open/verify each output as a fresh regular private file (existing symlinks/non-regular fail closed) → append snapshots/trajectory lines → stop interrupts any in-flight periodic wait and joins cleanly → mimalloc stats hook (`mi_register_output`) redirects allocator telemetry into the same private sink.
**Invariant:** Predictable names are acceptable ONLY with fail-closed type/ownership checks and O_NOFOLLOW-style semantics; shutdown latency must not depend on the sampling interval.
**Probe:** the three named tests plus `diagnostics_stalled_writer_cannot_retain_shutdown`, `diagnostics_placement_honors_tmpdir_with_spaces`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_diag_start", limit: 5 });
```

## Verdict
Adopt fail-closed temp-file discipline for any diagnostics writer; adapt naming (pid+tmpdir is inherently predictable — that's WHY the checks exist); omit the allocator-stats redirect if uninstrumented.
