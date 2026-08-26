<!-- capsule-v2 -->
# Snowflake ID generator — how do you mint unique i64 row IDs offline when the system clock can jump?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** What is the exact bit layout and the clock-skew policy of AppFlowy's local ID generator, and what must a porter never change?

## IDGenerator: 41|10|12 layout, panic-on-backwards
**Path/Symbol:** `frontend/rust-lib/flowy-server/src/local_server/uid.rs:IDGenerator` (:11-49).
**Signature:** `pub fn next_id(&mut self) -> i64`; constants `EPOCH=1637806706000`, `NODE_ID_BITS=10`, `SEQUENCE_BITS=12`.
**Data Shape:** id = `(timestamp-ms - EPOCH) << 22 | node_id << 12 | sequence`; monotonic per-process; node_id supplied by caller (device-scoped).

### Decisive source
```rust
// :27-44
let timestamp = self.timestamp();
if timestamp < self.last_timestamp {
  panic!("Clock moved backwards!");
}
if timestamp == self.last_timestamp {
  self.sequence = (self.sequence + 1) & SEQUENCE_MASK;
  if self.sequence == 0 { self.wait_next_millis(); }   // 4096 ids/ms then spin to next ms
} else { self.sequence = 0; }
self.last_timestamp = timestamp;
let id = ((timestamp - EPOCH) << TIMESTAMP_SHIFT)
       | (self.node_id << NODE_ID_SHIFT) | self.sequence;
```

**Flow:** Same-millisecond collisions burn sequence bits (12 ⇒ 4096 ids/ms/node); exhaustion spins (`wait_next_millis`) until the wall clock advances. Backwards clock movement is a HARD PANIC — the generator refuses to mint possibly-duplicate ids rather than risk colliding primary keys.
**Invariant:** Never widen/narrow the bit fields without migrating every persisted row; EPOCH is load-bearing (ids encode absolute time); two processes sharing a node_id WILL collide. The panic policy is intentional fail-fast: a porter "fixing" it into a clamp silently introduces duplicate-key corruption later.
**Probe:** Source-pinned byte-exact at HEAD (`IDGenerator::next_id` :25-44). Adversarial retrieval: query returns this file rank#1 in ext-appflowy, total:0 on ext-meetily. No dedicated unit test upstream for uid.rs at this pin (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "IDGenerator next_id wait_next_millis Clock moved backwards", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the layout + fail-fast skew policy wholesale. Adapt only EPOCH (fresh deployments). Omit nothing — the whole generator is ~50 lines.
