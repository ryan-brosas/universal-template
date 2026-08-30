<!-- capsule-v2 -->
# FTS manifest control record — how does a btree-backed file set prove its own integrity and currency?

**Source:** turso (MIT) `main@d9266124f` (/mnt/hdd/utopia/inspo/memory/turso); Codebase Memory `turso`. **Question:** What must the single persisted record contain so a reader answers "is my cache current?" AND "are the stored bytes intact?" from one decode?

## Incarnation + generation + per-file (size, chunks), checksum-sealed
**Path/Symbol:** `core/index_method/fts.rs`: `FtsControlRecord` (:313-317) + `from_catalog` (:328-354) + `encode` (:356-384) + `decode` (:386-466) + `validate_catalog` (:468-491), `fts_control_checksum` (:494-498), `stage_control_record` (:3239-3280).
**Signature:** `fn from_catalog(previous: Option<&Self>, index_incarnation: u64, catalog: &Catalog) -> Result<Self>` — generation = previous+1 (checked_add; exhaustion is InternalError "FTS manifest generation is exhausted") or 1 on first publish.
**Data Shape:** `{ magic[8], format_version: u32 LE, index_incarnation: u64, manifest_generation: u64, file_count: u32, [path_len u32 + path UTF-8 + size u64 + chunks u64]… , checksum u64 }`; files sorted by path before encode for deterministic bytes; Fnv1a-style checksum (0xcbf29ce484222325 / 0x100000001b3) over everything before the trailer.

### Decisive source
```rust
// fts.rs:304-311 — the record's dual purpose (verbatim):
/// The one persisted record that says what the index's storage currently
/// contains: which life of the index the bytes belong to
/// (`index_incarnation`), how many times the file set has been published
/// (`manifest_generation`), and the expected size and chunk count of every
/// file. It is written in the same transaction as the file bytes, so reading
/// it back answers two questions at once: "is my cached state still current?"
/// (compare incarnation + generation) and "are the stored files intact?"
/// (compare sizes and chunk counts).
```

**Flow:** every flush queues the control record into the SAME resumable btree write batch as the file chunks (stage_control_record → queue_write(FTS_CONTROL_PATH)) → readers decode with fail-closed validation at every step: truncation, bad magic, version mismatch, zero-chunks entry, duplicate path entry, trailing payload bytes all → Corrupt (:398-459) → validate_catalog cross-checks count AND per-path size/chunks against actual storage. Incarnation minting mixes root_page.rotate_left(32) ⊕ process counter ⊕ io.generate_random_number() so two processes creating the same index in different files never collide, with `.max(1)` because the placeholder value marks "never written" (:3247-3262).
**Invariant:** generation advance derives from THIS cursor's copy of the control record safely ONLY because writers are serialized — within a connection by the writer slot, across connections by pager write lock or MVCC write lease (the comment at :3266-3271 names all three). Port the record without that serialization and generations fork. Decode accepts NOTHING unverified: every length/offset uses checked arithmetic; the decoder is the integrity proof, not an afterthought.
**Probe:** `grep -n 'zero chunks\|duplicate FTS manifest\|trailing payload' core/index_method/fts.rs` hits :444/:452/:458 (fail-closed arms); `grep -c 'checked_' core/index_method/fts.rs` ≥ 6 inside decode/from_catalog; behavior pinned by tests/integration/index_method/ manifest-validation stats (manifest_validation_hits/misses exposed via IndexMethodTestStats :505-508).
**Retrieve:** search_graph "FtsControlRecord stage_control_record manifest_generation" resolves `turso.core.index_method.fts.FtsControlRecord` core/index_method/fts.rs :313-317.

## Verdict
Adopt the sealed-manifest pattern for any engine state stored as opaque files inside database rows: identity (incarnation) + publication counter (generation) + per-file integrity tuple, encoded deterministically, written atomically with the data it describes. Adapt field widths to your storage. Omit tantivy chunking specifics. Coverage: no_recorded_issue on fts.rs; decode arms verified by grep at HEAD.
