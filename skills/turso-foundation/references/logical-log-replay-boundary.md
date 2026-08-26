<!-- capsule-v2 -->
# MVCC logical-log replay boundary — how does recovery know WHICH transactions to re-apply without double-applying anything?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Where is the durable "replayed up to here" mark stored, and how do clock reseeding and torn tails compose with it?

## persistent_tx_ts_max watermark in a meta table + monotonic clock reset
**Path/Symbol:** `core/mvcc/persistent_storage/logical_log.rs:127-142` (recovery behavior block), meta constants `MVCC_META_TABLE_NAME` / `MVCC_META_KEY_PERSISTENT_TX_TS_MAX` (exported from `mvcc::database`, consumed in `checkpoint_state_machine.rs:11-13`), schema-before-data ordering guarantee (mod.rs BuildLogRecord docs), replay math :136-139.
**Signature:** read `persistent_tx_ts_max` from `__turso_internal_mvcc_meta` → stream frames in commit order → apply only frames with `commit_ts > watermark` → set clock to `max(watermark, max_replayed_commit_ts) + 1`.
**Data Shape:** the meta row is written IN THE SAME pager transaction as checkpointed data (checkpoint ordering step 2: "data + metadata row in same WAL txn"), so watermark and materialized state advance atomically — that atomicity IS the idempotence.

### Decisive source
```rust
// logical_log.rs:134-140 — the whole protocol:
// - reads `persistent_tx_ts_max` from `__turso_internal_mvcc_meta` (the durable replay boundary);
// - streams frames in commit order until first torn tail;
// - applies only validated frames whose `commit_ts > persistent_tx_ts_max`;
// - sets clock to `max(persistent_tx_ts_max, max_replayed_commit_ts) + 1`;
// - restores writer offset to `last_valid_offset` so torn-tail bytes are overwritten.
```
Why a strict inequality works: commit timestamps are strictly monotonic (PackedTs invariant), and the watermark is promoted atomically WITH the data it describes. A crash between log-append and checkpoint replays frames after the old watermark; a crash after checkpoint skips everything ≤ the new one. Clock reseeding guarantees newly minted timestamps never collide with either source. Schema rows serialized before data rows in each frame keep table-id → rootpage mappings ahead of their users during replay (:1493-1495 mod.rs).

**Flow:** boot → header validation (0-byte = no log; header-corrupt fails CLOSED) → read watermark → replay > watermark → reseed clock → truncate-tail repair via last_valid_offset.
**Invariant:** watermark promotion and data materialization share one transaction; replay must be a strict filter, never best-effort; the recovered clock must dominate every timestamp on disk.
**Probe:** module tests: `test_logical_log_read_multiple_transactions`, `test_logical_log_torn_tail_stops_cleanly`, `test_truncate_retained_when_uncheckpointed_frames_remain`; end-to-end restart probe tests.rs:2053 (clock reseeds monotonically).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "persistent_tx_ts_max mvcc_meta replay last_valid_offset", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt watermark-in-the-same-transaction for any redo log with idempotent replay requirements; adapt the meta store to your catalog. Omit the torn-tail overwrite trick only if your log format marks frame boundaries externally.
