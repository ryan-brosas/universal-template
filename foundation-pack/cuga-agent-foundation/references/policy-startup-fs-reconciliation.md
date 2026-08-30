<!-- capsule-v2 -->
# Startup policy FS↔storage reconciliation — what does validate_and_sync_policies ACTUALLY do to storage-only policies? (source wins over docstring)

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** If I port this bidirectional reconciliation verbatim, will policies that exist only in storage survive?

## validate_and_sync_policies: same-difference trap
**Path/Symbol:** `src/cuga/backend/server/main.py:validate_and_sync_policies` (1218–1272), called from lifespan after load_policies_from_folder.
**Signature:** `async def validate_and_sync_policies(storage, filesystem_sync) -> {"removed": int, "added_to_filesystem": int}`.
**Data Shape:** inputs are PolicyStorage (list/delete) and PolicyFilesystemSync (get_filesystem_policy_ids/save_policy_to_file); compares ID sets.

### Decisive source
```python
policies_to_remove = storage_policy_ids - fs_policy_ids        # step 1: delete storage-only rows
for policy_id in policies_to_remove:
    await storage.delete_policy(policy_id)
...
policies_to_save_to_fs = storage_policy_ids - fs_policy_ids    # step 2: SAME expression, stale list
for policy_id in policies_to_save_to_fs:
    policy = next((p for p in storage_policies if p.id == policy_id), None)
    if policy:
        filesystem_sync.save_policy_to_file(policy)            # file written — but row already deleted
```

**Flow:** docstring promises three reconciliations (fs→storage, storage→fs, deletions propagate). In reality steps 1 and 2 compute the identical difference against an UNCHANGED in-memory `storage_policies` snapshot: storage-only policies get deleted from storage AND materialized as markdown files. They re-enter storage only because startup earlier ran load_policies_from_folder(clear_existing=False) — i.e., convergence across restarts, but the function itself violates its documented contract mid-flight.
**Invariant (to port CORRECTLY):** recompute the storage-side diff AFTER mutations, or collect both directions before deleting; never iterate a set you just exhausted. The failure is contained (per-policy try/except, whole function returns zeroed stats on outer error) so startup never breaks.
**Probe:** upstream has NO direct test for this function (grep over tests/ finds none) — pinned by direct source read only; treat as source-only evidence and record the test gap when porting.
**Coverage caveat:** main.py is `metadata_changed` in check_index_coverage (recommended read_source_and_reindex) — satisfied here by full direct read of lines 543–1272 + endpoint ranges at HEAD 5de53ade.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "validate_and_sync_policies filesystem policy ids reconcile", limit: 5 });
```

## Verdict
Adapt the reconciliation INTENT with the bug fixed (two-phase compute, then apply); omit the buggy implementation as-is. Pair with the existing `policy-files.md` folder-sync capsule — that one covers the healthy save-on-write/remove-on-delete loop.
