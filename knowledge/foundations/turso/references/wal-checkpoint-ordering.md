<!-- capsule-v2 -->
# WAL checkpointing — which three ordering decisions carry checkpoint correctness?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** In what order must a checkpoint sync, copy, publish, and shrink — and under which locks?

## Five-state machine under ordered exclusive locks
**Path/Symbol:** `core/storage/wal.rs` Start → SyncWal → Processing → DetermineResult → Finalize; lock order documented :3105-3112 (CHECKPOINTER, then WRITER + read-mark 0 for Full/Restart/Truncate); SyncWal doc :2405-2422; mxSafeFrame :5130-5160; deferred truncation :5062-5068.
**Signature:** reads pipelined ≤ `MAX_INFLIGHT_READS = 512` into vectored writes with run-merging (WriteBatch tracks contiguous page-id runs via neighbor probes); flush when full, or len≥512 AND avg_run≥32, or drained. Auto-checkpoint fires when `max_frame > checkpoint_threshold + nbackfills` (default 1000).
**Data Shape:** backfill copies WAL frames into the DB file while readers may still need old versions from the WAL.

### Decisive source — the three ordering decisions
1. **WAL fsync BEFORE backfill** (:2405-2422): "Under synchronous=NORMAL commits do not fsync the WAL, so without this durability barrier a crash mid-backfill could persist some backfilled DB pages while recovery drops the unsynced WAL tail, leaving a torn database that matches no committed prefix." The barrier is issued after the frame range is fixed under the locks, so it covers exactly the frames being copied.
2. **mxSafeFrame clamping** (:5130-5160, porting sqlite wal.c): "A checkpoint must never overwrite a page in the main DB file if some active reader might still need to read that page from the WAL." Readers hold shared locks on their read-mark slots; the checkpointer only lowers FREE slots' values.
3. **Truncation deferred past DB sync** (:5062-5068): "For TRUNCATE mode, WAL truncation is NOT done here. It is deferred to pager.rs after the DB file has been synced… if a crash occurs after WAL truncation but before DB sync, the data would be lost." The checkpoint guard survives Finalize so no writer restarts the generation between DB-sync and nbackfills publication (:5085-5090).

Reads are ordered by frame id, writes by page id: "the more consecutive page IDs we submit together, the fewer overall write/writev syscalls." A stuck guard errors with "checkpoint stuck: no inflight completions but not complete" instead of hanging.

**Flow:** lock → fix frame range → fsync WAL → copy (read-by-frame, write-by-page) → sync DB → publish nbackfills → (deferred) truncate.
**Invariant:** sync the log before copying from it; sync the database before shrinking the log; hold the mutexes until the last durable fact is published.
**Probe:** wal.rs ~9770-9825 two readers at different snapshots assert Passive backfills exactly r1's max frame while r2 keeps reading; ~10310 asserts Busy FULL leaves nbackfills==0 ("must not publish positive nbackfills before DB sync") and rerun backfills from scratch; ~9930 asserts TRUNCATE leaves size 0 with checkpoint_seq==1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "checkpoint SyncWal mxSafeFrame nbackfills", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the durability-order ladder verbatim — it is the whole game in WAL maintenance; adapt batch/inflight constants to your IO lane; omit run-merging heuristics at small scale. Coverage caveat: none material.
