<!-- capsule-v2 -->
# Publish destination races — what happens if someone replaces the live DB while your index is running?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How does publication detect destination changes and refuse to destroy a backup-failed DB?

## Existence re-check + sidecar preservation veto
**Path/Symbol:** `src/pipeline/pipeline.c:prepare_publish_destination` (2440–2475).
**Signature:** `static int prepare_publish_destination(const char *final_path, bool final_existed, bool backup_succeeded, cbm_replacement_prepare_t *prepared);`
**Data Shape:** Captures `final_existed` BEFORE indexing; at publish time, if existence flipped ⇒ ABORT_PRESERVE_DB (someone else owns it now). If backup failed AND sidecars present ⇒ refuse (`backup_failed_sidecars_preserved`) because they may hold the only committed pages. If backup failed with no sidecars but the file IS unreadable ⇒ quarantine-then-replace.

### Decisive source
```c
bool final_exists_now = stat(final_path, &current_st) == 0;
if (final_exists_now != final_existed) {
    /* The destination appeared or vanished while we were indexing. Someone
     * else owns it now; leave whatever is there alone. */
    return CBM_PIPELINE_ABORT_PRESERVE_DB;
}
if (!backup_succeeded) {
    /* Sidecars alongside an un-copyable destination may hold the only
     * committed pages; refuse rather than drop them. */
```

**Flow:** pre-index stat → index → seal staging → prepare destination: existence delta check → missing ⇒ clear orphan sidecars only → backup-failed ⇒ sidecar veto or corrupt quarantine (never silent overwrite) → normal path seals+removes sidecars then renames.
**Invariant:** A vanished-or-appeared destination is ALWAYS someone else's; destructive replacement requires either a successful backup or provable corruption with no recoverable sidecars.
**Probe:** exercised via publish tests around pipeline.c:1996 call chain; rollback twins in quarantine-naming capsule; crash-recovery posture from bulk suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "prepare_publish_destination", limit: 5 });
```

## Verdict
Adopt before/after existence checks and sidecar-preservation vetoes for any atomic-replace publisher; adapt abort codes; keep "leave it alone" as the default on ambiguity.
