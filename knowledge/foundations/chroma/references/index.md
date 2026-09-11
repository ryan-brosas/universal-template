<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Chroma: Vector Database Foundation

## Use this for
Use when porting Chroma's embedded storage engine, building a vector store with HNSW + filter-then-search semantics, layering an in-memory batch over a persisted ANN index, compiling JSON where-filters into per-row subqueries, or implementing WAL-backed segment replication. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./hnsw-label-monotonicity.md` — How hnswlib integer labels stay stable across updates, resizes, and deletes.
- `./persistent-hnsw-layered-batch.md` — Why un-indexed writes must be served by a brute-force twin of the HNSW index.
- `./batch-operation-accounting.md` — Netting out add/update/delete counts when one ID is mutated repeatedly inside a batch.
- `./brute-force-index-free-list-tombstones.md` — Freelist + NaN-tombstone slot management for the bounded batch matrix.
- `./hnsw-params-validation-gate.md` — Where `hnsw:*` knobs are validated (propagation) vs defaulted (construction).
- `./where-filter-subquery-grammar.md` — Compiling `$eq/$ne/$in` filters into per-key row subqueries with IN/NOT IN.
- `./metadata-write-path.md` — The RETURNING-id insert ladder, typed value columns, and FTS upsert dance.
- `./sqlite-wal-returning-batch.md` — Multi-row WAL inserts whose returned seq_ids arrive unordered.
- `./wal-purge-coalesce-guard.md` — The min-across-segments purge rule that prevents deleting unreplayed log records.
- `./tx-nested-commit-gate.md` — Reentrant transactions that commit only at stack depth zero.
- `./maxscore-windowed-wand.md` — Windowed WAND with essential/non-essential terms over blockfile postings.
- `./topk-threshold-monotone.md` — A k-bound heap whose push() returns the live pruning threshold.
- `./sparse-directory-exact-count.md` — Overflow-safe document frequencies that refuse to fabricate saturated counts.
- `./two-pass-posting-suffix-rewrite.md` — Forked-blockfile commits that rewrite only blocks at or after the first delta.
- `./hnsw-provider-cache-version-gate.md` — Collection-keyed index cache with identity checks and double-checked loading.
- `./spann-version-tombstone-gc.md` — Version-map tombstones (version=0) and threshold-driven head GC.
- `./collection-name-s3-rules.md` — The five lexical rules every collection name must pass.
- `./dimension-lazy-pinning.md` — Writes pin collection dimensionality; queries only validate.
- `./version-mismatch-retry-ladder.md` — Whole-read retries on VersionMismatchError, not transient faults.
- `./delete-by-filter-limit-slice.md` — Delete guard clauses: no unconditional wipes, limit needs a filter.
- `./segment-manager-file-handle-lru.md` — rlimit-derived handle budgets with close-on-evict for mmap-heavy indexes.
- `./vector-encode-int32-decode-bug.md` — A latent upstream codec asymmetry a porter must fix, not copy.
- `./segment-api-plan-assembly.md` — Request → Scan/Filter/KNN/Limit/Projection plans; writes go WAL-only.

## Capsule map
- **HNSW label plane** — `hnsw-label-monotonicity`: labels are 1-based monotonic from total-added count; re-adds reuse the existing label via add_items update semantics; mark_deleted hides but never renumbers; apply order = index first, then mappings, then counter.
- **Layered write path** — `persistent-hnsw-layered-batch`: writes land in a bounded BruteForceIndex + current Batch until batch_size triggers _apply_batch; queries over-query HNSW by pending updates+deletes then two-pointer merge; count() adds batch delta to the persisted map size.
- **Batch accounting** — `batch-operation-accounting`: delete-after-in-batch-add nets out to zero counts and no tombstone; delete-after-update/upsert-update leaves a tombstone; upsert splits by exists_already flag into _upsert_add_ids.
- **Brute-force twin** — `brute-force-index-free-list-tombstones`: fixed numpy matrix + dict indexes; visibility = allocated ∧ not-deleted ∧ allowed; distance fn chosen once by space so scores merge cleanly with HNSW.
- **Params validation** — `hnsw-params-validation-gate`: unknown-key rejection lives in extract()/propagate_collection_metadata at create-time; constructors only apply defaults (space=l2, ef=100, M=16, batch=100, sync=1000).
- **Filter planner** — `where-filter-subquery-grammar`: every operator compiles to `embeddings.id [NOT] IN (subquery WHERE key=? AND <typed value predicate>)`; numeric ops OR int_value|float_value columns; $ne/$nin invert membership, not rows.
- **Metadata write path** — `metadata-write-path`: INSERT…RETURNING id catches IntegrityError for update routing (never INSERT OR REPLACE, it changes the PK); None values delete keys; bool checked before int; FTS keyed by internal id needs delete-then-insert on replace.
- **WAL producer** — `sqlite-wal-returning-batch`: one multi-row INSERT into embeddings_queue with RETURNING seq_id,id; RETURNING order is unspecified so results are reordered via an id→index map before notification; max_batch_size derived from PRAGMA MAX_VARIABLE_NUMBER / 6 variables per record.
- **WAL retention** — `wal-purge-coalesce-guard`: purge deletes only seq_id < MIN(per-segment max_seq_id), COALESCE(-1) so any never-flushed segment freezes retention; auto-purge defaults on only for fresh systems.
- **Transaction nesting** — `tx-nested-commit-gate`: thread-local tx stack; BEGIN on depth 1, commit/rollback only when the outermost exits; case_sensitive_like set at both sites.
- **Sparse retrieval** — `maxscore-windowed-wand`: 4096-doc windows, per-window term re-sort by window_score, prefix-sum picks essential terms, non-essential terms scored only against budget-filtered candidates; SIMD filter_competitive matches scalar exactly.
- **Top-K heap** — `topk-threshold-monotone`: inverted BinaryHeap keeps the min at peek; push returns the current threshold so WAND can prune without extra reads.
- **Posting statistics** — `sparse-directory-exact-count`: u32 posting_count extension; counts too big to fit are LEFT UNCOUNTED rather than saturated, because a fabricated df collapses IDF and silently drops the term.
- **Incremental indexing** — `two-pass-posting-suffix-rewrite`: commit = pass 1 posting blocks sorted by encoded dim, pass 2 directory parts; untouched prefix blocks are carried by the forked blockfile, counts reconciled against stored vs suffix sums with header recount fallback.
- **Index lifecycle** — `hnsw-provider-cache-version-gate`: cache key is collection UUID, entry validity requires index.id match; open/fork use double-checked locking around spawn_blocking loads; flush fans out 4 hnswlib files with try_join_all.
- **SPANN maintenance** — `spann-version-tombstone-gc`: delete writes version=0 tombstone; update of version 0 errors; eligible_to_gc compares len_with_deleted against (1+threshold%)×live; GC rebuilds a clean HNSW and swaps atomically.
- **Name rules** — `collection-name-s3-rules`: length 3–63, alphanumeric ends, middle `[A-Za-z0-9._-]`, no `..`, IPv4 rejected — enforced on create AND rename.
- **Dimension contract** — `dimension-lazy-pinning`: first write pins sysdb dimension and caches in-model; queries validate-only so an empty collection can't be dimension-poisoned.
- **Read consistency** — `version-mismatch-retry-ladder`: exactly 3 retries @2s on VersionMismatchError only, reraise=True; wraps whole plan+execute, never fragments.
- **Delete guards** — `delete-by-filter-limit-slice`: at least one targeting argument required; limit validated (bool≠int) and restricted to filter deletes; zero matches short-circuit before WAL submit.
- **Handle budget** — `segment-manager-file-handle-lru`: RLIMIT_NOFILE ÷ per-segment handle count bounds open persistent indexes; eviction closes handles; instance creation lock-serialized.
- **Codec caveat** — `vector-encode-int32-decode-bug`: INT32 decode reads float32 dtype at this pin — symmetric codecs required; assert-on-pin probe catches drift both ways.
- **Plan assembly** — `segment-api-plan-assembly`: reads build Scan/Filter/KNN/Limit/Projection via one sysdb scan; writes only produce OperationRecords into the WAL; documents/uris ride as chroma:document/chroma:uri metadata keys.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Chroma (Apache-2.0), `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory project `ext-chroma` (33,972 nodes / 205,526 edges, FULL mode, generation 2026-08-23T09:40:15Z, generation_matches=true; parse_partial limited to SQL migrations/k8s YAML/proto files, none cited).

## Full view (memory graph)
Revalidate `ext-chroma` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. All cited Python paths resolve line-exact via BM25 search_graph (`{"project":"ext-chroma","query":"...","detail":"ids"}` positional-JSON form). Direct-test corpus: upstream pytest suites under `chromadb/test/segment/` and `chromadb/test/db/` (require hnswlib/onnx runtime — not run here); Rust side ships a dedicated maxscore integration corpus `rust/index/tests/maxscore/ms_01..ms_21` (cargo runner available but full build skipped this pass).

## Boundaries
Adopt the label/monotonicity contract, batch net-out semantics, NOT-IN subquery grammar, RETURNING reorder rule, COALESCE purge guard, WAND window/threshold mechanics, and version-tombstone model — these are portable invariants. Adapt file layouts (persist_directory/<segment_id>, hnswlib's four-file format) and PRAGMA-derived batch limits to your host. Omit Chroma's distributed Rust worker planes (query/frontend/log-service coordination, s3heap, memberlist, metering), the JS/Go client SDKs, auth/quota/rate-limit middleware, telemetry, and OpenTelemetry instrumentation — they are deployment surfaces, not reusable engine contracts.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`batch-operation-accounting.md`](./batch-operation-accounting.md)
- [`brute-force-index-free-list-tombstones.md`](./brute-force-index-free-list-tombstones.md)
- [`collection-name-s3-rules.md`](./collection-name-s3-rules.md)
- [`delete-by-filter-limit-slice.md`](./delete-by-filter-limit-slice.md)
- [`dimension-lazy-pinning.md`](./dimension-lazy-pinning.md)
- [`hnsw-label-monotonicity.md`](./hnsw-label-monotonicity.md)
- [`hnsw-params-validation-gate.md`](./hnsw-params-validation-gate.md)
- [`hnsw-provider-cache-version-gate.md`](./hnsw-provider-cache-version-gate.md)
- [`maxscore-windowed-wand.md`](./maxscore-windowed-wand.md)
- [`metadata-write-path.md`](./metadata-write-path.md)
- [`persistent-hnsw-layered-batch.md`](./persistent-hnsw-layered-batch.md)
- [`segment-api-plan-assembly.md`](./segment-api-plan-assembly.md)
- [`segment-manager-file-handle-lru.md`](./segment-manager-file-handle-lru.md)
- [`spann-version-tombstone-gc.md`](./spann-version-tombstone-gc.md)
- [`sparse-directory-exact-count.md`](./sparse-directory-exact-count.md)
- [`sqlite-wal-returning-batch.md`](./sqlite-wal-returning-batch.md)
- [`topk-threshold-monotone.md`](./topk-threshold-monotone.md)
- [`two-pass-posting-suffix-rewrite.md`](./two-pass-posting-suffix-rewrite.md)
- [`tx-nested-commit-gate.md`](./tx-nested-commit-gate.md)
- [`vector-encode-int32-decode-bug.md`](./vector-encode-int32-decode-bug.md)
- [`version-mismatch-retry-ladder.md`](./version-mismatch-retry-ladder.md)
- [`wal-purge-coalesce-guard.md`](./wal-purge-coalesce-guard.md)
- [`where-filter-subquery-grammar.md`](./where-filter-subquery-grammar.md)
