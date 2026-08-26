<!-- capsule-v2 -->
# Quarantine naming — how do you move a corrupt DB aside without colliding with previous quarantines or orphaning sidecars?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What rename protocol handles `.corrupt` name races and WAL/-shm sidecars atomically enough?

## 10000-candidate scan + sidecar moves + rollback on partial failure
**Path/Symbol:** `src/pipeline/pipeline.c:quarantine_existing_generation` (1556–1602) + `rollback_quarantined_generation` (1517–1547).
**Signature:** `static int quarantine_existing_generation(const char *db_path, cbm_replacement_prepare_t *prepared);`
**Data Shape:** Candidate names: `<db>.corrupt`, then `<db>.corrupt.<1..9999>`; a candidate is available only when NEITHER it nor its `-wal`/`-shm` sidecars exist. `cbm_rename_noreplace` everywhere — never overwrite. On any sidecar move failure, roll the main rename back.

### Decisive source
```c
for (int attempt = 0; attempt < 10000; attempt++) {
    ... candidate = attempt == 0 ? "<db>.corrupt" : "<db>.corrupt.<attempt>" ...
    bool available = !replacement_path_exists(candidate);
    for (... "-wal", "-shm" ...) available &= !replacement_path_exists(sidecar);
    if (!available) continue;
    if (cbm_rename_noreplace(db_path, candidate) != 0) {
        if (replacement_path_exists(candidate)) continue;  /* lost a race: next name */
        return CBM_PIPELINE_PERSIST_FAILED;
    }
    prepared->quarantined = true;
    for (...) { ... on failure: rollback_quarantined_generation(...); }
```

**Flow:** scan candidates → first fully-available name wins → rename main DB → move each existing sidecar → any failure rolls everything back and reports PERSIST_FAILED. Distinct from publish-side quarantine (`quarantine_invalid=false`) whose destination is private staging debris that should be DELETED, not parked.
**Invariant:** Never clobber an existing `.corrupt*`; never leave a DB renamed while its WAL stays behind; staging debris must not pollute the user's db directory under uninterpretable names.
**Probe:** `tests/test_store_checkpoint.c:dump_install_ignores_stale_wal_sidecar`, `remove_db_sidecars_rejects_truncated_suffix_path`; daemon twin `tests/test_daemon_application.c:daemon_application_recovers_with_unique_per_job_quarantine_files`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "quarantine_existing_generation", limit: 5 });
```

## Verdict
Adopt noreplace candidate scanning + sidecar-aware rollback; adapt suffix scheme; keep the two-destination distinction (user data vs own debris).
