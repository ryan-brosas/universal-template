<!-- capsule-v2 -->
# Seal-for-publish — how do you make a staging DB self-contained before an atomic rename?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What is the exact checkpoint/journal-mode sequence that guarantees the main DB file alone carries every committed page, and why must you read the PRAGMA result back?

## Seal then verify
**Path/Symbol:** `src/store/store.c:cbm_store_seal_for_atomic_publish` (1406–1463).
**Signature:** `int cbm_store_seal_for_atomic_publish(cbm_store_t *s);`
**Data Shape:** Returns OK only when (a) `synchronous=FULL` set, (b) TRUNCATE checkpoint moved ALL frames (`checkpointed == log`), (c) `PRAGMA journal_mode=DELETE` actually entered delete mode. Any shortfall → ERR.

### Decisive source
```c
rc = sqlite3_wal_checkpoint_v2(s->db, NULL, SQLITE_CHECKPOINT_TRUNCATE, &log_frames, &checkpointed_frames);
if (rc != SQLITE_OK || (log_frames >= 0 && checkpointed_frames != log_frames)) return CBM_STORE_ERR;
...
/* PRAGMA journal_mode returns the mode SQLite actually entered. sqlite3_exec
 * would discard that result and could falsely report a successful seal. */
rc = sqlite3_prepare_v2(s->db, "PRAGMA journal_mode = DELETE;", ...);
... bool is_delete = mode && sqlite3_stricmp(mode, "delete") == 0;
```

**Flow:** restore strongest durability (`synchronous=FULL`) → TRUNCATE checkpoint with frame-count equality check → switch journal_mode to DELETE and VERIFY the returned mode string → caller now owns one self-contained file safe for atomic rename.
**Invariant:** Never trust `sqlite3_exec` for journal_mode; never rename a staging DB whose WAL still holds un-checkpointed frames; seal runs only on an exclusively-owned staging connection.
**Probe:** `tests/test_store_checkpoint.c:seal_for_atomic_publish_makes_main_file_self_contained` (raw second connection reads mode=="delete", marker row present) and `seal_for_atomic_publish_fails_closed_while_reader_pins_wal`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_seal_for_atomic_publish", limit: 5 });
```

## Verdict
Adopt the seal-then-verify sequence and the frame-equality check; adapt the raw-second-connection verification into your own integration test; omit the Windows wide-path re-seal variant unless you publish through SQLite's win VFS.
