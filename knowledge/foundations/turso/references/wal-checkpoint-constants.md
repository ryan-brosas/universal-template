<!-- capsule-v2 -->
# Checkpoint constants — which concurrency budgets trade which named failures?

**Source:** turso (Turso) MIT `main@def9a0601b8ead82675e672e1843447251b15fb4`; Codebase Memory `turso`. **Question:** What does each tuning constant buy, and where do the levers live?

## The constants block, read as documentation
**Path/Symbol:** `core/storage/wal.rs:2424-2433`.
**Data Shape:** CKPT_BATCH_PAGES=512 (IOV_MAX=1024 headroom), MIN_AVG_RUN_FOR_FLUSH=32.0, MIN_BATCH_LEN_FOR_FLUSH=512, MAX_INFLIGHT_WRITES=64, MAX_INFLIGHT_READS=512.

### Decisive source
```rust
// IOV_MAX is 1024 on most systems, lets use 512 to be safe
pub const CKPT_BATCH_PAGES: usize = 512;
/// TODO: *ALL* of these need to be tuned for perf. It is tricky
/// trying to figure out the ideal numbers here to work together concurrently
const MIN_AVG_RUN_FOR_FLUSH: f32 = 32.0;
const MIN_BATCH_LEN_FOR_FLUSH: usize = 512;
const MAX_INFLIGHT_WRITES: usize = 64;
pub const MAX_INFLIGHT_READS: usize = 512;
pub const IOV_MAX: usize = 1024;
```
(wal.rs:2424-2433; flush condition wired at :2501/:2599; appends assert `pages.len() <= IOV_MAX`)

**Flow:** Processing pipelines reads (≤ MAX_INFLIGHT_READS) into vectored writes with run-merging — WriteBatch tracks contiguous page-id runs via neighbor probes; flush when full, or len≥512 AND avg_run≥32, or drained. Reads ordered by frame id, writes by page id: "the more consecutive page IDs we submit together, the fewer overall write/writev syscalls." A stuck guard errors "checkpoint stuck: no inflight completions but not complete" instead of hanging.
**Invariant:** Every number trades a NAMED failure for throughput: IOV headroom avoids EINVAL on differing platforms; inflight caps bound queue depth so a huge checkpoint cannot monopolize the IO lane; the run-length heuristic avoids tiny scattered writev's yet stays prompt on drain; recovery reads use frame-aligned 16MB chunks amortizing syscalls without splitting frames. Auto-checkpoint fires at `max_frame > checkpoint_threshold + nbackfills` (default 1000).

**Probe:** wal.rs:~10210-10240 asserts FULL backfill equals mx_before; ~9840-9925 asserts incremental passive checkpoints sum to r2's frame with row counts preserved.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "CKPT_BATCH_PAGES MAX_INFLIGHT_READS WriteBatch avg_run_len", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pin-every-budget-to-a-named-constant-with-its-failure-comment as practice; adopt the specific numbers as starting points. Adapt counts to your IO lane depth; keep the loud TODO admitting which numbers are guesses.
