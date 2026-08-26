<!-- capsule-v2 -->
# Hermitage isolation contract — which SQL anomalies does this MVCC actually prevent, and where does it deliberately stop?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** If I port this MVCC, what isolation level do I claim, and which anomalies will my users still hit?

## Snapshot isolation with EAGER write-write conflicts — not serializable
**Path/Symbol:** `core/mvcc/database/hermitage_tests.rs:11-24` (contract header), 25 test fns :104-891 (`test_hermitage_g0_write_cycles_prevented` … `test_hermitage_g2_anti_dependency_cycles`, `test_hermitage_write_write_conflict`).
**Signature:** harness `MvccTestDbNoConn` drives two concurrent txs through the public read/write/commit API; each test maps one Hermitage anomaly.
**Data Shape:** documented outcome matrix — prevents G0, G1a, G1b, G1c, OTV, PMP, P4 (lost update), G-single (read skew); does NOT prevent G2-item (write skew) or G2 (anti-dependency cycles).

### Decisive source
```rust
// hermitage_tests.rs:14-23 — the claim under test:
//   - Snapshot is taken at BEGIN (not at first read like FoundationDB)
//   - Write-write conflicts are detected immediately at write time (WriteWriteConflict),
//     NOT deferred to commit (like FoundationDB)
//   - Transactions never see uncommitted changes from other active transactions (no dirty reads)
//   - Isolation level: snapshot isolation (prevents G0, G1a, G1b, G1c, OTV, PMP, P4, G-single)
//   - Does NOT prevent G2-item (write skew) or G2 ... those require serializable
// :18-20 — comparison row:
//   FoundationDB (serializable): writes succeed locally, conflict checked at commit time.
//   Turso: fails eagerly at write time (WriteWriteConflict), no blocking.
```
The suite is adapted from ept/hermitage (the standard isolation test battery). Snapshot-at-BEGIN is a load-bearing difference from first-read systems: it fixes what "concurrent" means for the conflict predicate and pairs with the atomic begin-publish window. Write-skew (G2-item) remaining possible is BY DESIGN of snapshot isolation — porters claiming serializable from this code will be wrong.

**Flow:** each anomaly = scripted interleaving of two txs → assert either the observed read set or the exact `WriteWriteConflict` failure.
**Invariant:** when you port, re-run this matrix against YOUR eager/deferred choices — changing where conflicts fire moves tests P4/G-single outcomes, and claiming serializable without G2 prevention is a correctness lie to users.
**Probe:** `core/mvcc/database/hermitage_tests.rs` itself is the probe suite (25 tests); run via `cargo test hermitage`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "hermitage write skew snapshot isolation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the outcome matrix as your porting acceptance test; adapt anomaly scripts to your API. Omit nothing — the negative results (write-skew allowed, snapshot-at-begin) are as much the contract as the positive ones.
