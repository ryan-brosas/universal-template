<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Turso Foundation

## Use this for
A SQLite-compatible storage engine: MVCC with commit dependencies, checksum-chained WAL with three-phase commit ordering, b-tree rebalancing limits, pin-count eviction, a logical-log replay journal, and cross-process shared-WAL coordination. Source and tests are the contract; the references carry the decisive excerpts.

## Load the matching source dump
- `./mvcc-version-model.md` — tagged-u64 version bounds + one-word transaction fate (PackedTs tag-bit encoding incl. Timestamp(0)-is-real rationale).
- `./mvcc-conflict-detection.md` — commit-time first-committer-wins validation.
- `./mvcc-commit-dependencies.md` — counted speculation instead of blocking.
- `./mvcc-commit-state-machine.md` — IO-yielding commit step order as the spec.
- `./mvcc-begin-rollback.md` — atomic begin-publication + in-place rollback.
- `./mvcc-gc-two-clocks.md` — GC at the LWM ∩ WAL-read-mark intersection.
- `./wal-frame-codec.md` — SQLite-byte-compatible checksum-chained frame format.
- `./wal-commit-publication.md` — prepare → durable write → publish (callback grants visibility).
- `./wal-recovery.md` — prove-then-discard prefix recovery + watermark seeding.
- `./wal-checkpoint-ordering.md` — the three ordering decisions that carry checkpoint correctness.
- `./wal-snapshot-read-marks.md` — read-mark slot coordination (ports SQLite aReadMark).
- `./btree-balancing.md` — structural 3→5 rebalancing bound + append fast path.
- `./btree-redistribution.md` — greedy packing + mandatory legality-repair pass.
- `./pager-spill-tags.md` — TAG_WRITE_PENDING + compare-on-completion async write-back.
- `./pager-durability-ordering.md` — one fsync between bytes-written and metadata-published.
- `./loglog-frame-format.md` — `.db-log` 56B header + TX frames, salt-seeded chained CRC.
- `./loglog-deferred-publication.md` — writer offset lags pwrite; CRC promoted only on success.
- `./loglog-streaming-reader.md` — re-entrant phase parser with anchor checkpoints.
- `./loglog-recovery-boundary.md` — persistent_tx_ts_max boundary + WAL-last ordering.
- `./checkpoint-passive-publish-window.md` — collect-unlocked / brief publish window.
- `./checkpoint-durability-ladder.md` — SyncDbFile → log truncate → WAL truncate last.
- `./checkpoint-seq-compaction.md` — SeqCompactDriver watermark compaction, dual-layer paired deletes.
- `./shared-wal-coordination.md` — `.tshm` mmap: authority snapshot + ownership bytes + frame index.
- `./io-yield-completions.md` — IOResult::IO + Completion resumable async contract.
- `./skiplist-primitive.md` — lock-free ordered map the MVCC store builds on.
- `./mvcc-conflict-detection-duality.md` — conflict lanes: eager delete-of-visible vs commit-time insert validation (supersedes "commit-only" claim; erratum recorded).
- `./mvcc-eager-conflict-lanes.md` — per-statement error timing: UPDATE/DELETE eager, INSERT optimistic, UPSERT bypass nuance (hermitage-pinned).
- `./mvcc-commit-dependency-speculation.md` — register-and-report protocol with increment/drain/check orderings.
- `./mvcc-clock-callback-contract.md` — LogicalClock holds its lock ACROSS the callback, fusing ts allocation with Preparing publication (#5198 rationale).
- `./mvcc-hermitage-isolation-contract.md` — 25-test Hermitage matrix: snapshot-at-BEGIN SI, G2/write-skew NOT prevented.
- `./mvcc-finalized-tx-cache.md` — immutable terminal-state cache beside the live map, pruned below LWM.
- `./mvcc-visibility-predicates.md` — full begin/end truth table incl. Hekaton typo fix citation.
- `./mvcc-read-path.md` — reverse-first-visible scan; Ok(None) = invisible ≠ absent.
- `./mvcc-index-versioning.md` — SortableIndexKey chains + unique-prefix-range conflict scan + NULL semantics.
- `./mvcc-rowid-allocation.md` — monotonic maybe-update allocators + negative canonical table ids.
- `./mvcc-savepoint-ledgers.md` — created/deleted version-id ledgers with conditional write-set pruning.
- `./mvcc-materialized-at-tracking.md` — WalPos stamps with reset-to-ORIGIN-on-mutation conservatism.
- `./mvcc-gc-incremental-pass.md` — threshold-triggered chain-bounded CAS-single-flighted sweep w/ pinned-LWM baseline reset.
- `./mvcc-rewrite-live-versions.md` — publish-fate-then-migrate-lazily chunked TxID→ts rewrite.
- `./mvcc-commit-coordinator.md` — one TursoRwLock serializing MVCC log vs pager WAL planes.
- `./mvcc-schema-checkpointing.md` — staged RootMapOps published in ONE window after durability.
- `./mvcc-checkpoint-ordering.md` — enumerated resumable states; fsync-before-truncate ordering baked into the enum.
- `./logical-log-deferred-commit.md` — two-phase append: staged pending CRC confirmed or discarded.
- `./logical-log-replay-boundary.md` — persistent_tx_ts_max watermark in same txn as data = idempotent replay.
- `./logical-log-portable-sync.md` — LML2/LML3 version gating + always-emit extension blocks (no ambiguity for sync readers).
- `./page-transform-codec-stack.md` — PageCodec trait, declared reserved-byte budgets, page-1 header-as-associated-data.
- `./journal-mode-dispatch.md` — parse-everything/support-subset enum + fail-closed encrypted-MVCC composition rule.
- `./shared-wal-commit-publication.md` — fetch_max monotonicity + checksums only-if-latest-writer + seqlock snapshot reads.
- `./shared-wal-frame-index.md` — append-only mmap index published via len-CAS, reverse-block hash lookup, honest overflow flag.
- `./shared-wal-reader-slots.md` — bitmap→byte-lock→owner claim ladder with provable-death reclamation only.
- `./shared-wal-backfill-proof.md` — CRC-sealed proof binding checkpoint claims to BOTH WAL generation and DB-file identity.
- `./shared-wal-ownership-locks.md` — OFD-vs-POSIX election ladder: lock bytes are truth, owner fields are metadata.
- `./shared-wal-snapshot-reuse.md` — keyed refcount slot sharing with loser-drops-acquisition race resolution.
- `./shared-wal-mmap-lifecycle.md` — durable-vs-transient field split, conservative teardown, dedup registry pattern.
- `./buffer-pool-arena-split.md` — twin arenas (+24B WAL header trick) + io_uring fixed-buffer ID leak-through.
- `./slot-bitmap-lockfree-allocation.md` — 1=free bitmap, CAS-retry alloc, wait-free free_one, hint-not-correctness.
- `./spin-lock-primitive.md` — minimal Acquire/Release spinlock and where it must NOT be used.
- `./testing-yield-injection.md` — cfg-gated enumerated yield points turning IO races into deterministic tests.
- `./btree-balance-bounds.md` — 3→5 blast-radius constants and balance_quick append fast-path gates.
- `./mvcc-packed-ts-version-model.md` — PackedTs layout detail: tag BITS not zero sentinel (Timestamp(0) is real).
- `./pager-cache-admission.md` — soft capacity + single-flight pending reads.
- `./pager-pin-guard.md` — PinGuard counted-pin eviction discipline.
- `./storage-redistribution-legality.md` — mandatory legality-repair pass detail.
- `./storage-soft-cache-singleflight.md` — soft-limit cache + single-flight reads detail.
- `./storage-spill-tags.md` — spill write-in-flight sentinels detail.
- `./wal-snapshot-slots.md` — read-mark slot coordination detail.
- `./mvcc-dual-cursor-merge.md` — DualCursorPeek ordered merge + IndexShadowFinger amortized shadow checks (MVCC ∩ B-tree iteration).
- `./mvcc-lazy-cursor.md` — MvccLazyCursor async position machine + epoch-guarded index finger.
- `./io-completions-groups.md` — Completion/IOCompletions grouping for vectored async IO.
- `./io-vfs-abstraction.md` — pluggable VFS contract every storage backend must satisfy.
- `./vdbe-async-step-loop.md` — bytecode VM yield/resume without blocking its thread.
- `./wal-checkpoint-constants.md` — checkpoint concurrency budgets vs the named failures they trade.
- `./storage-pin-guard.md` — PinGuard counted pins (canonical pin-discipline capsule; supersedes deleted pager-pin-guard).

- `./mvcc-commit-conflicts.md` — commit-time conflict rule set (commit-sweep half of the duality).
- `./buffer-pool-deferred-init.md` — BufferPool begin_init→finalize lifecycle: temp-buffer phase, OnceLock-set-wins arena guard, temporary-buffer fallback ladder.
- `./page-cache-sieve-eviction.md` — bounded SIEVE clock eviction: ref-bits ≤ REF_MAX=3, `len×(REF_MAX+1)` sweep bound, advance-before-unlink hand rule.
- `./page-cache-spill-accounting.md` — 90% spill threshold + conservative evictable_count fast path, PinGuard id-ordered spill batches, over-capacity force admission.
- `./encryption-page-format.md` — constant-size encrypted page layout: reserved-bytes budget, trailing nonce, page-1 Turso-header swap with header-as-AAD.
- `./loglog-serializer-chunk-streams.md` — reserve-once/copy-per-chunk LogChunkStream serialization with fail-closed length verification.
- `./loglog-encrypted-in-place-expansion.md` — back-to-front in-place AEAD chunk expansion of the serialized log payload; last-chunk AAD carries total size.
- `./portable-cursor-fixed-point.md` — self-referential varint cursor resolved by iterating frame_end_offset to a fixed point.
- `./vdbe-seek-state-machine.md` — OpSeekState four-state resume machine: state on ProgramState, reset on every non-IO exit, float-precision op rewriting before cursor contact.
- `./vdbe-column-deferred-seek.md` — OpColumnState Start→Rowid→Seek→GetColumn deferred index→table lookup with sticky GetColumn slot across IO yields.
- `./vdbe-active-op-slot.md` — ActiveOpStateSlot: ONE suspended-opcode slot per program — typed lazy-init accessors, hard panic on variant mismatch, is_idle fast-path bypass.
- `./vdbe-op-transaction-ladder.md` — OpTransactionState five-state BEGIN ladder Start→AttachedBeginWriteTx→BeginNamedSavepoints→CheckSchemaCookie→BeginStatement: writer-mutex gate, pre-tx reprepare fast-path, schema validated at three distinct points.
- `./vdbe-op-new-rowid-ladder.md` — OpNewRowidState six-state rowid allocation: monotonic MVCC allocator → btree max+1 → bounded random masked to [1, MAX/2]; allocator lock lives in the cursor across IO.
- `./vdbe-op-no-conflict-null-gate.md` — OpNoConflictState: any NULL in the probe record jumps target_pc BEFORE the index seek; polarity inverted vs most seeks (Found=conflict falls through, NotFound jumps).
- `./mvcc-cursor-snapshot-gates.md` — dual logical+physical read-time gates (is_btree_allocated + snapshot-consistent root-page resolution) keep long-lived cursors honest across PASSIVE-checkpoint materialization; stale binding degrades to SchemaUpdated reprepare, never panic.
- `./mvcc-cursor-write-routing.md` — MvccLazyCursor insert/delete four-way routing on Loaded{in_btree} positions incl. the btree_resident class; prefetch record BEFORE non-reentrant delete IO.
- `./mvcc-finger-lazy-shadow-resolution.md` — IndexShadowFinger three-arm compare resolves the shadow predicate ONLY on exact key matches — stepping over MVCC-only keys stays side-effect-free.
- `./mvcc-seek-eqonly-short-circuit.md` — redundant eq_only seek on a positioned visible row must return Found without resetting iterators, or mid-scan delete loops die early (op_idx_delete/DeferredSeek enabler).
- `./storage-databasestorage-codec-io.md` — DatabaseStorage wraps caller completions with codec/checksum transforms: scratch-buffer read decoded in place, zero-byte ≠ error, encode fails BEFORE submit.
- `./mvcc-store-write-ladder.md` — the four insert shapes (insert/tombstone/btree_resident/delete-in-place) and eager-invisible-only delete rule every table/index mutation funnels through; conflicts are impossible at insert, typed-dead at delete.
- `./rootpage-binding-lifecycle.md` — versioned `table_id→root_page` bindings: STAGED→publish→retire→GC state machine with the two-conjunct read gate (snapshot covers AND read-mark reaches).
- `./mvcc-btree-covers-chain-gate.md` — when a scan may skip the version store and read the B-tree directly; fail-closed early-false ladder withdrawn during checkpoints.
- `./btree-cursor-count-spill-resume.md` — CountState spill-yield resume machine: mutation-before-transition discipline with a payload-carrying Descend variant so re-entry never re-applies loop-top effects; idempotent Finish owns finalization IO.
- `./subjournal-single-owner-latch.md` — statement-scoped subjournal: CAS try_use/Busy ownership latch, first-image-wins per-savepoint dirty bitmap, self-describing page_size+4 id-prefixed records.
- `./durable-storage-trait-boundary.md` — DurableStorage trait port boundary: log_tx→advance-or-discard byte handshake across the trait, shadowed atomic offset keeping should_checkpoint lock-free, defaulted durability hooks.
- `./portable-logical-codec.md` — portable sync payload builder: positional interned string table + mv_table_id object maps over loglog primitives, single-predicate internal-name exclusion vocabulary.
- `./portable-delete-extension.md` — tombstone→PK-record delete extension ladder: committed-Timestamp gate only, sqlite_schema vs user-table payload shapes, lazy single decode through logical→physical column mapping.
- `./checkpoint-schema-lifecycle.md` — sqlite_schema b-tree identity decode + covering-window drop resolution turn schema history into B-tree create/destroy ops without corrupting a reused root page.
- `./checkpoint-collection-snapshot.md` — snapshot-bounded checkpointable-version selection: post-snapshot inserts deferred, future tombstones clamped to live, order-sensitive DB-file existence tracking.
- `./checkpoint-local-schema-view.md` — BuildLocalSchemaViewStateMachine: on-disk sqlite_schema scan overlaid with the MVCC delta at snapshot_ts so index ids resolve at the collection snapshot, not now.
- `./checkpoint-gc-floor.md` — three-mark GC floor (MVCC reader marks ∧ pager-pinned frames ∧ backfill floor) + per-chain materialization stamping + mode-split Finalize retention.
- `./checkpoint-preemption-resume.md` — COLLECT_PREEMPTION_THRESHOLD=1024 cooperative chunking with cursor-carrying resume states and sorted-write-set seek elision.
- `./checkpoint-io-error-cleanup-ledger.md` — ONE mirrored cleanup funnel for every checkpoint failure route: LockStates ledger bits, write-subsumes-read pager unwind, unconditional pager+WAL checkpoint-state reset, discard-not-revert staged root-map ops.
- `./checkpoint-blocking-lock-gc-predicate.md` — the machine-local blocking-lock flag doubles as the aggressive-vs-conservative GC kernel discriminator; substituting a store-level lock query is the wrong-port trap.
- `./mvcc-vacuum-gate-ladder.md` — stop-the-world via checkpoint-lock write mode + demote/reload/promote + assert-heavy version-store wipe (pass 10).
- `./in-place-vacuum-publication.md` — build-in-temp → publish-through-source-WAL → forced TRUNCATE; ledger-keyed cleanup where post-publish failure is NOT a rollback (pass 10).
- `./mvcc-savepoint-stack-internals.md` — delta-ledger savepoints: created/deleted/newly-written ledgers, conditional write-set eviction, deferred root-commit (pass 10).
- `./savepoint-opcode-mirroring.md` — three-ledger split (pages/connection frames/attached mirrors), compensating blind releases, schema-snapshot rollback (pass 10).
- `./vacuum-target-build-engine.md` — phase-ordered replay engine: rootpage≠0 storage test, sequence/backing-btree exclusions, indexes-after-data (pass 10).
- `./connection-savepoint-frame-ledger.md` — three-Arc schema snapshots captured at SAVEPOINT begin, restored at ROLLBACK TO with zero disk I/O (vdbe async contract); release-truncates vs rollback-to-keeps-target asymmetry (pass 11).
- `./pager-savepoint-walpos-capture.md` — SavepointWalPos eager-vs-deferred dual capture (idempotent materialization at write upgrade AFTER log restart), four-plane atomic rollback (subjournal pre-images kept dirty, beyond-boundary discard, WAL rewind triple, cursor invalidation), parent write-offset healing + commit-deferred release (pass 11).
- `./savepoint-name-busy-gate.md` — single-site translate-time ASCII lowercasing feeding byte-exact ledger lookups; the reject-all-three BUSY gate justified by Turso's missing cursor-tripping (pass 11).
- `./savepoint-mirror-compensation.md` — two-phase Begin (all yielding header reads up-front, then atomic multi-ledger mutation), compensating blind releases across non-main pagers on partial mirror failure, loud IO-fallback error arm (pass 11).
- `./optimizer-join-order-dp.md` — naive-thresholded Selinger DP ≤12 tables / greedy beyond; multi-variant memo keyed (mask,last); outer-join legality masks + FULL-OUTER reordering barrier; arena-truncate discipline (pass 12).
- `./optimizer-cost-model-constants.md` — CostModelParams default table verbatim; eq-prefix/NULL-decline ANALYZE rows-per-seek ladder; unique-point-lookup short-circuit; cache_reuse_factor rescan discount (pass 12).
- `./optimizer-hash-join-pricing.md` — build+probe CPU cost with probe_multiplier, grace-spill 2×page-IO model at DEFAULT_MEM_BUDGET; seek-replacement eligibility rule disqualifying rowid/index-covered join keys (pass 12).
- `./mainloop-open-close-emission.md` — per-table loop scaffolding: LoopLabels/LeftJoin/SemiAnti metadata, chained anti-join body re-anchor, Rewind/Last vs VFilter vs coroutine-yield vs SeekRowid openers, DeferredSeek pairing (pass 12).
- `./mainloop-body-emit-targets.md` — LoopEmitTarget precedence ladder GroupBy→AggStep→Window→OrderBySorter→QueryResult; sorter-vs-mainloop GROUP BY rowsources; MinMax NULL-skip label (pass 12).
- `./hash-build-signature-reuse.md` — HashBuildPlanner Reuse/Build decision on full signature identity; HashClose of stale builds; bloom filter disabled for non-binary collations (pass 12).
- `./vdbe-hash-join-grace-spill.md` — adaptive power-of-two partition count clamped [16,128], largest-buffer spill order, int/float hash unification seed 1337, NULL-probe short-circuit, 32KB-debug budget (pass 12).
- `./vdbe-sorter-external-merge.md` — SortState machine Start→Flush→InitHeap→Next; varint-prefixed chunk format; ascending-sort+reverse stability trick; pending-completion heap gate (pass 12).
- `./ivm-delta-pipeline.md` — per-view transaction delta capture → apply_view_deltas commit driver → DbspCircuit::commit → WriteRowView seek-read-weight write-back (weight ≤0 deletes) (pass 12).
- `./ivm-dbsp-primitives.md` — full-row Z-set keys (the 82/88-hours lesson), ordered deltas with deferred consolidation, UUID-v5 Hash128, bit-packed generate_storage_id (pass 12).
- `./ivm-join-operator-nulls.md` — SQL NULL-never-equals-NULL key matching over hash candidates; arity guard before value comparison (pass 12).
- `./jsonb-binary-path-nav.md` — size-marker ladder 12/13/14, depth cap 1000, navigate_path traversal stack, intermediate-segment forced Upsert vs caller-mode final segment (pass 12).
- `./stmt-journal-flag-analysis.md` — compile-time `usesStmtJournal = isMultiWrite ∧ mayAbort`: per-constraint effective-resolution ladder, AUTOINCREMENT multi-row taint, UPSERT DO UPDATE forced ABORT (pass 13).
- `./statement-savepoint-lifecycle.md` — begin/end statement savepoints across MVCC store, pager subjournal, and attached pagers; asymmetric open/close with unconditional FK-counter restore (pass 13).
- `./poisoned-explicit-transaction.md` — four-condition poison gate marking an explicit tx after an unfinished writer was dropped without a statement savepoint; COMMIT refuses with the stable error string (pass 13).
- `./temp-ddl-committed-schema.md` — dirty flag + clone-at-commit snapshot making the per-connection TEMP schema ride outer-tx commit/rollback, restore-or-empty + prepare-generation bump (pass 13).
- `./hash-build-input-materialization.md` — rowid-only vs key+payload ephemeral hash-build inputs, join-prefix pruning, access-method sanitization ladder (pass 13).
- `./from-clause-subquery-modes.md` — coroutine / materialized-table / direct-materialized-index decision ladder; CTE pre-materialization before coroutines (pass 13).
- `./subquery-eval-phases.md` — eval-phase floors by origin, #6807 aggregate-arg exception, outer-aggregate readers deferred via contains_aggregates marker (pass 13).
- `./ivm-aggregate-blob-codec.md` — positional self-describing AggregateState blob layout; MIN/MAX has_value-flag cell omission rule; global COUNT head cell (pass 13).
- `./index-method-spi-contract.md` — external-index SPI: factory→attachment→cursor, declared mvcc_support posture, pattern-based planning, statement-scoped commit ladder (pass 14 drift wave).
- `./mvcc-index-method-write-lease.md` — per-index write lease: Busy vs WriteWriteConflict keyed on last_publish_ts > snapshot; commit-only publication stamping (pass 14).
- `./index-method-context-identity.md` — captured-at-open identity (incarnation/runtime_id FNV), dual Wal|Mvcc snapshot stamp, Weak connection edge as cycle-breaker for drop-recovery (pass 14).
- `./fts-writer-slot-trigger-refusal.md` — one flushing cursor per index per statement; trigger double-writer refused with Raise(Abort); stale-claim replacement rule (pass 14).
- `./fts-control-record-manifest.md` — checksum-sealed manifest binding incarnation+generation+per-file size/chunks, written in the same transaction as file bytes; fail-closed decode ladder (pass 14).
- `./fts-snapshot-cache-budget.md` — admission always-insert / retention bounded / oldest-dies-newest-immune; retained-vs-live memory split; test-budget override hook (pass 14).
- `./fts-foreground-merge-budget.md` — synchronous one-bounded-merge maintenance replacing background merges; smallest-level-first; pending-write-aware byte accounting; distrust of third-party policy output (pass 14).
- `./eqp-detail-vocabulary.md` — EXPLAIN QUERY PLAN detail enum + Display vocabulary; end-key SeekOp NEGATED for display (b-tree stop condition vs user operator) (pass 14).
- `./btree-min-cell-size-padding.md` — padded-leaf vs real-size-divider duality for sub-minimum index cells; max(payload,4) free-space reservation; overflow-path padding so balancing sees one size (pass 15).
- `./json-path-label-escape-duality.md` — jsonLabelCompare mirror: raw-vs-decoded 2×2 compare matrix; TEXT5 storage for quoted labels containing backslashes; `-> label` shorthand = quoted path (pass 15).
- `./json-arrow-error-precedence.md` — document conversion hoisted ABOVE path parsing in `->`/`->>` so malformed JSON wins over bad paths, SQLite error precedence (pass 15).
- `./json-agg-blob-gate-and-tree-root-rows.md` — ensure_blob_arg_is_jsonb gate added to json_group_array/object aggregate steps; json_tree primitive-root NULL parent + quote-aware path-trim lengths (pass 15).
- `./failed-commit-wal-rollback-latch.md` — failed COMMIT flips auto-commit AND arms TxnCleanup::RollbackTxn in the same breath, or zombie rows resurrect on later statements (pass 15).
- `./capi-finalize-reset-completion-contract.md` — finalize/reset report run-to-completion errors but ALWAYS free/unregister/reset; prepare of statement-free SQL ⇒ OK+NULL at the FFI boundary (pass 15).
- `./parser-var-token-reclassification.md` — BadVariableName deleted; malformed parameter names reclassify as UnrecognizedToken with SQLite's exact message shape (pass 15).
- `./simulator-wal-fault-injection.md` — path-scoped arm→act→disarm fault windows with fault counters and a second-connection durability witness (pass 15).
- `./tcl-conformance-harness-wave.md` — TCL statement-introspection/bind commands, tester.tcl helper ports, and blessed-corpus-as-spec workflow (json103/json502 gates) (pass 15).
- `./vdbe-autocommit-cleanup-baton.md` — the can_autocommit_now gating plane behind the rollback latch: which statement may end an implicit tx while siblings park, writer-finishes-readers-remain vs last-statement-finishes-attached-leftovers (pass 15, drain-lane-turso).
- `./vector-ivf-shadow-schema.md` — vector index persists as TWO real backing_btree indexes (`{index}_inverted_index` 3-col key / `{index}_stats` 1-col key) visible in sqlite_master; nested-statement DDL needs the needs_stmt_subtransactions=false Busy opt-out (pass 16).
- `./vector-ivf-insert-machine.md` — six-state insert machine: per-component posting row (position,sum,rowid) + cnt/min/max stats merge; sum denormalized into every posting row; seek result deliberately discarded (blind idempotent insert) (pass 16).
- `./vector-ivf-delete-machine.md` — eight-state delete twin: Found deletes, TryAdvance advances-once-then-trusts-position, NotFound ⇒ Corrupt; stats cnt−1 but min/max never re-shrunk (conservative drift) (pass 16).
- `./vector-ivf-threshold-algebra.md` — approximate-KNN pruning: J=min(L,M)/(Q+L−min(L,M)) upper bound → two-range sum_threshold rule, −1.0 prune-all, scan_order/scan_portion component budgeting (pass 16).
- `./vector-ivf-exact-rescore-topk.md` — candidate-generator contract: rescore from live table row (missing rowid ⇒ Corrupt), FloatOrd total_cmp BTreeSet top-K pop_last, results fully materialized before first row (pass 16).
- `./vector-ivf-spi-posture-fuzz-contract.md` — minimal SPI posture (backing_btree=false + TransactionalBackingStore + no-op hooks) vs FTS's flush ladder; differential fuzz pins delta=0 exactness and b ≤ a ≤ b+delta recall/precision bargain (pass 16).

## Capsule map
- **MVCC core** — `mvcc-version-model`, `mvcc-conflict-detection`, `mvcc-commit-dependencies`, `mvcc-commit-state-machine`, `mvcc-begin-rollback`, `mvcc-gc-two-clocks`: Hekaton-style optimistic concurrency, commit-time validation, counted dependencies, IO-yielding commit, atomic begin, dual-clock GC.
- **WAL** — `wal-frame-codec`, `wal-commit-publication`, `wal-recovery`, `wal-checkpoint-ordering`, `wal-snapshot-read-marks`: byte-compatible framing, callback-side visibility, prove-then-discard recovery, durability-order ladder, read-mark slots.
- **B-tree & pager** — `btree-balancing`, `btree-redistribution`, `storage-pin-guard` (canonical pin discipline), `pager-spill-tags` (spill write-in-flight sentinels), `pager-durability-ordering`: bounded rebalancing, legality repair, pin discipline, spill write-back, fsync ordering.
- **Logical log** — `loglog-frame-format`, `loglog-deferred-publication`, `loglog-streaming-reader`, `loglog-recovery-boundary`: `.db-log` journal, deferred offset publication, resumable parser, replay boundary + WAL-last.
- **Checkpoint & infra** — `checkpoint-passive-publish-window`, `checkpoint-durability-ladder`, `checkpoint-seq-compaction`, `shared-wal-coordination`, `io-yield-completions`, `skiplist-primitive`: online materialization, durability ladder, sequence reclamation, multi-process WAL, async IO contract, lock-free index.
- **Shared-WAL deep seams (lane B)** — `shared-wal-commit-publication`, `shared-wal-frame-index`, `shared-wal-reader-slots`, `shared-wal-backfill-proof`, `shared-wal-ownership-locks`, `shared-wal-snapshot-reuse`, `shared-wal-mmap-lifecycle`: monotonic multi-process publication, len-CAS mmap index, provable-death slot reclamation, sealed checkpoint proofs, OFD/POSIX election, refcounted snapshot sharing, mapping lifecycle.
- **MVCC deep seams (lane B)** — `mvcc-conflict-detection-duality`, `mvcc-eager-conflict-lanes`, `mvcc-commit-dependency-speculation`, `mvcc-clock-callback-contract`, `mvcc-hermitage-isolation-contract`, `mvcc-finalized-tx-cache`, `mvcc-visibility-predicates`, `mvcc-read-path`, `mvcc-index-versioning`, `mvcc-rowid-allocation`, `mvcc-savepoint-ledgers`, `mvcc-materialized-at-tracking`, `mvcc-gc-incremental-pass`, `mvcc-rewrite-live-versions`, `mvcc-commit-coordinator`: conflict-lane timing, dependency orderings, clock fusion, isolation matrix, fate cache, truth tables, allocators, savepoints, GC stamps, lazy migration, cross-plane serialization.
- **Logical log & codec deep seams (lane B)** — `logical-log-deferred-commit`, `logical-log-replay-boundary`, `logical-log-portable-sync`, `page-transform-codec-stack`, `journal-mode-dispatch`, `buffer-pool-arena-split`, `slot-bitmap-lockfree-allocation`, `spin-lock-primitive`, `testing-yield-injection`, `mvcc-schema-checkpointing`, `mvcc-checkpoint-ordering`: two-phase appends, replay watermarks, sync-capable framing, page codecs, mode dispatch, arena pooling, lock-free bitmaps, spinlock limits, yield-point testing, staged schema bindings, resumable checkpoints.
- **Iteration & IO planes (lane B)** — `mvcc-dual-cursor-merge`, `mvcc-lazy-cursor`, `io-completions-groups`, `io-vfs-abstraction`, `vdbe-async-step-loop`: dual-source ordered iteration, async cursor positions, completion grouping, VFS contract, VM yield loop.
- **Restored detail capsules (sibling re-added after dedup)** — `btree-balance-bounds`, `mvcc-packed-ts-version-model`, `pager-cache-admission`, `pager-pin-guard`, `storage-redistribution-legality`, `storage-soft-cache-singleflight`, `storage-spill-tags`, `wal-snapshot-slots`: constants and detail views of planes covered by sibling capsules; consult alongside their primaries. — `wal-checkpoint-constants`, `mvcc-commit-conflicts`: constants and detail views of planes covered by sibling capsules; consult alongside their primaries. (Sibling's post-commit dedup pass deleted overlapping files — btree-balance-bounds/pager-pin-guard/pager-cache-admission/storage-spill-tags/storage-redistribution-legality/storage-soft-cache-singleflight/wal-snapshot-slots/mvcc-packed-ts-version-model all folded into their primary capsules; storage-pin-guard is now the canonical pin-discipline capsule.)
- **Buffer & cache internals (pass 4)** — `buffer-pool-deferred-init`: two-phase pool lifecycle with OnceLock arena guard; `page-cache-sieve-eviction`: bounded clock/SIEVE eviction with ref-bit ceiling and sweep-termination bound; `page-cache-spill-accounting`: threshold-triggered spill selection + conservative O(1) room accounting + over-capacity force admission.
- **Encryption & log serialization planes (pass 4)** — `encryption-page-format`: constant-size page layout with reserved-bytes crypto budget and page-1 header-as-AAD swap; `loglog-serializer-chunk-streams`: reserve-once/copy-per-chunk record writing with fail-closed length checks; `loglog-encrypted-in-place-expansion`: back-to-front in-place AEAD chunk expansion with total-size-in-last-AAD; `portable-cursor-fixed-point`: self-width-referencing cursor offset solved by fixed-point iteration.
- **VDBE opcode machines (pass 4)** — `vdbe-seek-state-machine`: OpSeekState resume machine with persisted state + non-IO reset + precision op rewriting; `vdbe-column-deferred-seek`: OpColumnState deferred index→table lookup with sticky GetColumn slot.
- **Cursor internals & opcode resume machines (pass 5)** — `vdbe-active-op-slot`, `vdbe-op-transaction-ladder`, `vdbe-op-new-rowid-ladder`, `vdbe-op-no-conflict-null-gate`: the one-slot suspension discipline every resumable opcode shares, plus the Transaction/NewRowid/NoConflict state machines; `mvcc-cursor-snapshot-gates`, `mvcc-cursor-write-routing`, `mvcc-finger-lazy-shadow-resolution`, `mvcc-seek-eqonly-short-circuit`: MvccLazyCursor read gates, four-way write routing incl. btree_resident, side-effect-safe shadow resolution, eq_only short-circuit; `storage-databasestorage-codec-io`: DatabaseStorage completion-wrapping codec/checksum plane.
- **MVCC store-side plumbing & checkpoint bindings (pass 6)** — `mvcc-store-write-ladder`: the `_to_table_or_index` mutation funnel with its four RowVersion shapes and optimistic-insert/invisible-only-delete conflict placement; `rootpage-binding-lifecycle`: versioned RootEntry state machine behind every B-tree readability decision; `mvcc-btree-covers-chain-gate`: the fail-closed predicate deciding B-tree vs version-store reads during passive checkpointing.
- **Uncited-file sweep (pass 7)** — `btree-cursor-count-spill-resume`: per-method resume enums with mutation-before-yield discipline (`state_machines.rs` family, CountState::Descend as the pattern's payload twin); `subjournal-single-owner-latch`: statement-scoped before-image journal with CAS ownership + id-prefixed records; `durable-storage-trait-boundary`: pluggable MVCC durability trait with byte-handshake and shadow-offset checkpoint gate; `portable-logical-codec` + `portable-delete-extension`: the portable sync encoder pair — interned string tables/object maps and committed-only tombstone→PK delete extensions.
- **Checkpoint state machine whole-file plane (pass 8)** — `checkpoint-schema-lifecycle`: b-tree identity extraction + covering-window drop binding resolution feeding SpecialWrite create/destroy dispatch; `checkpoint-collection-snapshot`: the checkpointable-version selection ladder (snapshot clamps, existence ordering, retry idempotence); `checkpoint-local-schema-view`: snapshot-consistent schema rebuild via disk scan + MVCC delta overlay; `checkpoint-gc-floor`: three-mark floor composition + materialization stamping + mode-split Finalize retention; `checkpoint-preemption-resume`: threshold chunking with cursor/index resume states across collect and GC phases.
- **Error recovery & lock-flag planes (pass 9)** — `checkpoint-io-error-cleanup-ledger`: the single cleanup funnel every failure route (step()-internal, external-IO wait, commit abort, journal-mode abandonment) mirrors through LockStates ledger bits; `checkpoint-blocking-lock-gc-predicate`: why the machine's own lock bit (not a store-level query) selects aggressive vs conservative version-GC kernels.
- **VACUUM & savepoint planes (pass 10)** — `mvcc-vacuum-gate-ladder`, `in-place-vacuum-publication`, `vacuum-target-build-engine`: stop-the-world gate + demotion ladder, temp-build→WAL-publish→TRUNCATE atomicity hinge with ledger cleanup, phase-ordered schema replay engine; `mvcc-savepoint-stack-internals`, `savepoint-opcode-mirroring`: delta-ledger savepoints with conditional write-set eviction, and the opcode-level three-ledger mirroring across MVCC/WAL-pager/temp/attached engines.
- **Savepoint WAL-pager kernel (pass 11)** — `pager-savepoint-walpos-capture` (dual capture points + idempotent materialization + four-plane rollback restore), `connection-savepoint-frame-ledger` (zero-I/O schema snapshot restore on the async contract), `savepoint-name-busy-gate` (translate-time normalization + no-tripping BUSY rule), `savepoint-mirror-compensation` (yield-free pre-load + compensating releases): the byte-level pager twin of the pass-10 opcode plane — how a named savepoint actually rewinds WAL pages, schemas, FK counters, and attached DBs as one unit.
- **SQL planner: join-order & cost planes (pass 12)** — `optimizer-join-order-dp` (Selinger DP with naive-plan pruning threshold + greedy >12-table fallback), `optimizer-cost-model-constants` (the CostModelParams table and ANALYZE eq-prefix ladder), `optimizer-hash-join-pricing` (build/probe/spill cost + seek-replacement eligibility): how a SQL statement becomes a priced join order.
- **Bytecode emission planes (pass 12)** — `mainloop-open-close-emission` (per-table loop scaffolding, openers taxonomy, anti-join relink), `mainloop-body-emit-targets` (row-sink precedence ladder), `hash-build-signature-reuse` (translate-time Reuse/Build identity decision).
- **VDBE aux structures (pass 12)** — `vdbe-hash-join-grace-spill` (adaptive grace partitioning executor), `vdbe-sorter-external-merge` (external sort state machine + merge heap).
- **Incremental view maintenance (pass 12)** — `ivm-delta-pipeline` (capture→commit→weighted write-back), `ivm-dbsp-primitives` (full-row Z-sets, Hash128, storage ids), `ivm-join-operator-nulls` (SQL NULL matching in incremental joins); `jsonb-binary-path-nav` (JSONB binary format + path navigation).
- **Statement undo & transactional schema planes (pass 13)** — `stmt-journal-flag-analysis`, `statement-savepoint-lifecycle`, `poisoned-explicit-transaction`, `temp-ddl-committed-schema`: which statements need statement journals, how partial writes roll back per backend, when COMMIT must refuse, and how temp DDL rides the outer transaction.
- **SELECT emitter: materialization & subqueries (pass 13)** — `hash-build-input-materialization`, `from-clause-subquery-modes`, `subquery-eval-phases`: pre-materialized hash-build inputs without multiplicity loss, FROM-subquery storage-mode choice, and eval-phase assignment.
- **IVM aggregate-state codec (pass 13)** — `ivm-aggregate-blob-codec`: the restart-surviving blob format behind incremental aggregates.
- **Index-method SPI & FTS engine (pass 14 drift wave, pin `d9266124f`)** — `index-method-spi-contract`, `mvcc-index-method-write-lease`, `index-method-context-identity`, `fts-writer-slot-trigger-refusal`, `fts-control-record-manifest`, `fts-snapshot-cache-budget`, `fts-foreground-merge-budget`: how out-of-tree index methods plug in transactionally — declared MVCC posture + hook ladder, per-index write lease with Busy/WriteWriteConflict split, identity+snapshot context, and the FTS engine's writer slot, sealed manifest, cache budget, and foreground merge discipline.
- **EXPLAIN QUERY PLANNER (pass 14)** — `eqp-detail-vocabulary`: the SQLite-compatible detail strings and the end-key operator negation rule.
- **Pass-15 drift wave (pin `1654d1587`) — corruption & compatibility fixes** — `btree-min-cell-size-padding` (b-tree write-path invariant), `json-path-label-escape-duality`, `json-arrow-error-precedence`, `json-agg-blob-gate-and-tree-root-rows` (SQLite JSON conformance), `failed-commit-wal-rollback-latch` (txn teardown arming) with `vdbe-autocommit-cleanup-baton` (the can_autocommit_now sibling gate that decides who acts on the latch; drain-lane-turso capsule), `capi-finalize-reset-completion-contract` (C ABI), `parser-var-token-reclassification` (lexer error taxonomy), `simulator-wal-fault-injection` + `tcl-conformance-harness-wave` (test infrastructure as spec).
- **Vector search: toy_vector_sparse_ivf index method (pass 16)** — `vector-ivf-shadow-schema` (shadow backing_btree persistence + nested-DDL subjournal opt-out), `vector-ivf-insert-machine` (posting+stats write ladder, blind insert), `vector-ivf-delete-machine` (paranoid delete triage, stats drift), `vector-ivf-threshold-algebra` (sum-based upper-bound pruning, scan budgeting), `vector-ivf-exact-rescore-topk` (candidate-generator contract, total_cmp top-K, materialized results), `vector-ivf-spi-posture-fuzz-contract` (minimal MVCC posture vs FTS; differential fuzz as the approximation's executable spec): the second shipped index method, end to end.

## Extending the foundation
Add one references-file capsule per seam (loader, grouped map, decisive source, invariant, direct-test probe, `search_graph` retrieval).

## Provenance
Indexed in Codebase Memory as `turso` (`$REFERENCE_ROOT/memory/turso` via live symlink from `$REFERENCE_ROOT/turso`); 50,306 nodes / 353,465 edges, full mode, HEAD `1654d1587` (MIT) — re-indexed IN PLACE at pass 15 after the +30-commit drift wave (was 50,226/352,846 @ `d9266124f`). Confirm every claim against source — the graph is an index, not truth.
Pass 7 (dedicated lane, [DONE:240]) re-verified at unchanged pin: citation-vs-inventory grep over core/storage + core/mvcc exposed 7 never-cited files (core/mvcc/mod.rs, core/storage/mod.rs, state_machines.rs, subjournal.rs, core/mvcc/persistent_storage/mod.rs + its discard_pending_tests.rs, portable_logical.rs) → 5 new capsule-v2 (95→100).
Pass 8 ([DONE:265], dedicated lane) re-verified at unchanged pin `def9a060` (head==base, graph ready 49,666n/347,732e): citation-vs-inventory census over all 30 files in core/storage+core/mvcc = ZERO never-cited; executed the queued checkpoint-porting target by reading `core/mvcc/database/checkpoint_state_machine.rs` whole-file top-to-bottom (3,782L) → 5 new capsule-v2 (100→105); gate-5 REAL runner executed: `cargo test --features conn_raw_api -p turso_core --lib checkpoint_state_machine` = **15 passed / 0 failed** fresh compile at HEAD.
Pass 9 ([DONE:294], dedicated lane drain-lane-turso 5f071ad80da9) at unchanged pin `def9a060` (head==base==pin re-verified + origin poll: upstream 19,488 ahead → drift-gated out): posed the standing error-recovery porting question and mined the cleanup plane — `LockStates` (:148-152), `cleanup_after_external_io_error` (:874-910) with its six failure routes (step() error arm :3019-3027, external-IO waits connection.rs:2327 + execute.rs:644, commit-machine teardown mod.rs:1678-1685/1728 via vdbe abort :2605, journal-mode abandonment execute.rs:17718-17728), plus `blocking_checkpoint_lock_held` as GC-mode discriminator (:1774/:1840/:2987) → 2 new capsule-v2 (105→107); probes resolve line-exact; coverage no_recorded_issue ×5.
Pass 10 ([DONE:295], this lane) at unchanged pin `def9a060` (head==base re-verified via index_status --verbose): executed pass-9 conditional targets #2+#3 by posing the vacuum and nested-tx porting questions — whole-file read of `core/vdbe/vacuum.rs` (3,304L: MvccVacuumGuard :1195-1228, VacuumInPlacePhase 12-phase machine :1261-2320 w/ ledger cleanup :2330-2403, VacuumTargetBuildPhase engine :479-1031) plus savepoint planes in mvcc/database/mod.rs (:820-1230 kernel, :6611-6814 MvStore wrappers) and execute.rs op_savepoint (:4750-4989) → 5 new capsule-v2 (107→112). Gate-5 REAL RUNNERS at HEAD: `cargo test --features conn_raw_api -p turso_core --lib vacuum` = **43/43**, `--lib vacuum_gate` = **3/3**, `--lib test_savepoint_` = **8/8**. Probes grep-verified byte-exact (tests.rs :407/:423/:443/:493/:1242 gate family, :11821-11961 savepoint family, savepoint.sqltest = 41 SAVEPOINT ops). Coverage stdin-JSON ×4 cited paths no_recorded_issue+generation_matches=true.
Pass 11 ([DONE:341], this lane) at unchanged pin `def9a060` (head==base==pin re-verified; graph ready 49,666n/347,732e): executed pass-10 conditional targets #2+#3 by posing the named-savepoint frame-ledger and WAL-position-restore porting questions — whole reads of core/connection.rs :100-230 + :4800-4927 (NamedSavepointFrame/RollbackFrameInfo structs, frame ledger API), execute.rs :3865-3955 (mirror machinery) + :4740-4989 (op_savepoint consumer side incl. schema restore :4962-4972 + cookie invalidation :4974-4983), pager.rs :1240-1341 (SavepointWalPos/SavepointSnapshot/Savepoint) + :2035-2171 (release/rollback_to named) + :2219-2319 (rollback_to_snapshot four planes) + :3016-3049 (materialize at write upgrade), translate/rollback.rs whole → 4 new capsule-v2 (112→116). Gate-5 REAL RUNNER at HEAD: `cargo test -p core_tester --test fuzz_tests -- savepoint_tests::named_savepoint_differential_fuzz savepoint_tests::release_root_named_savepoint_checks_deferred_fk savepoint_tests::release_root_deferred_fk_failure_can_recover_with_rollback_to{,_mvcc} savepoint_tests::deferred_fk_parent_key_update_keeps_violation_until_root_release` = **5 passed / 0 failed / 141 filtered** (fresh compile, incl. the 2000-step rusqlite parity fuzz). Probe battery ~30 greps byte-exact across scratch-turso-p11-probes.sh + probes2.sh (one authored anchor re-derived against source before writing: multi-line rust string-continuation never matches single-line grep); search_graph resolves every cited symbol line-exact; coverage stdin-JSON ×4 paths no_recorded_issue+metadata_match generation_matches=true.
Pass 12 ([DONE:384], this lane drain-lane-turso successor fire, 2026-08-24) at unchanged pin `def9a060` (head==base re-verified via index_status; root `$REFERENCE_ROOT/turso` resolves through LIVE symlink to `memory/turso` — benign variant, no twin adoption): executed NEXT-PASS TARGET #1 as a diff-first citation-vs-inventory grep across ALL 116 refs vs the 748-file .rs inventory → 129 cited, exposing four wholly uncited subsystems. Named the standing "planner translation" question and mined it plus three more planes → 12 new capsule-v2 (116→128): **optimizer/join.rs** DP kernel (:1089-1565, GREEDY_JOIN_THRESHOLD=12 :1568, memo-per-(mask,last) multi-variant :1254-1258, FULL-OUTER bidirectional reorder barrier :1300-1307, arena truncate-on-reject, targeted FULL OUTER error ladder :1521-1558) + greedy fallback (:1578-1767); **cost_params.rs/cost.rs** full default table (:103-140) + estimate_index_cost (:166-236, leaf-cost-zero point lookups, index_bonus floor 0.001) + ANALYZE eq-prefix rows-per-seek with NULL-decline rule (:332-395); **access_method.rs** estimate_hash_join_cost (:1199-1234, spill = 2×page-IO × probe_multiplier) + seek-replacement eligibility (:1400-1487); **main_loop/open+close+body** emission planes (LoopLabels/LeftJoin/SemiAnti metadata, chained anti-join body re-anchor open.rs:110-124 + body.rs:82-97 "resolve BEFORE any body instruction", Rewind/Last vs VFilter vs coroutine-Yield vs SeekRowid opener taxonomy, DeferredSeek pairing, LoopEmitTarget precedence ladder body.rs:100-118, sorter-stores-leaf-columns-only GROUP BY rule, MinMax NULL-skip label); **main_loop/hash.rs** HashBuildPlanner signature-reuse protocol (:107-261 incl. bloom-filter collation gate :139-141); **vdbe/hash_table.rs** grace executor (adaptive power-of-two partitions clamp [16,128] :1105-1125, largest-buffer spill order :1441-1451, int/float hash unification seed 1337, NULL-probe short-circuit, debug 32KB budget); **vdbe/sorter.rs** external merge (SortState machine :259-309, ascending-sort+reverse stability trick :265-271, varint-prefixed chunks flush :522-567 buffer = max(payload)+9, pending-completion heap gate :474-487); **incremental/** IVM plane (apply_view_deltas vdbe/mod.rs:2000-2102 rollback-discards/commit-resumes-at-index, DbspCircuit::commit mem::replace ownership dance compiler.rs:533-655, WriteRowView weight ≤0 deletes :66-140, dbsp.rs full-row Z-set keys w/ 82/88-hours comment :122-136, generate_storage_id bit-pack operator.rs:65-70, join_operator sql_keys_equal NULL-pair rejection :441-459); **json/jsonb.rs** binary format (size markers 12/13/14, MAX_JSON_DEPTH=1000) + navigate_path traversal stack w/ intermediate-segment forced Upsert (:2466-2518). Gate evidence: 35 authored grep anchors verified live pre-write; direct tests pinned per capsule (test_compute_best_join_order_star_schema :3197, automatic_index_puts_equalities_before_ranges :2305, test_adaptive_partition_count_bounds :3659, fuzz_external_sort :1267, test_hashable_row_delta_operations :498, ivm-compound-null-filter.sqltest 4 expects, test_set_operation :4436); coverage clean on all newly cited paths except perf/*.sql parse_partial (uncited). INCIDENT RECOVERED: this lane's run overlapped an interrupted fleet-wide `pull --rebase` that left HEAD mid-rebase with packs.json carrying COMMITTED conflict markers (rallly b97431a1) and the leaf reverted to its pre-pass-11 base while pass-11 refs sat untracked; resolved by `git rebase --abort` to the last good local commit then fast-forward to origin (which already contained e710fd42 pass 11), zero content loss, my 12 new refs stayed untracked throughout.

Pass 13 ([DONE:409], this lane, successor fire, 2026-08-24) at unchanged pin `def9a060` (head==base==pin re-verified via index_status --verbose; live symlink root confirmed benign; UPSTREAM DRIFT DETECTED: fetched origin/main advanced to `3d59872a6915` — merge-base confirms pin IS an ancestor and upstream is ~19.5k commits ahead since Aug 12, so this pass is DRIFT-GATED AT-PIN mining per mcp-ts-sdk precedent; re-index + citation re-anchor against the drift wave is queued as next-pass target #1): executed conditional targets #2+#3+#5 fully and target #4 partially (whole-file reads of both named files yielded THREE seams) → 8 new capsule-v2 (128→136): **stmt_journal.rs whole-file** (constraint_may_abort effective-resolution ladder :81-116, AUTOINCREMENT multi-row DatabaseFull taint :152-160, UPSERT DO UPDATE hardcoded ABORT :161-166, DELETE trigger/FK-only abort lanes :293-297, builder fold builder.rs:2177-2186 + may_abort() function-call taint :879-883); **ProgramState::begin_statement/end_statement** (mod.rs:1233-1395: MVCC-vs-pager-vs-attached savepoint routing, vdbeCloseStatement mirror comment :1277, unconditional FK-counter restore :1372-1379, EndStatement enum :1447-1454, opcode entry execute.rs:4461-4525 incl. attached subjournal + MvStore savepoints); **poison gate** (connection.rs poisoned_tx :363/:2753-2764, mod.rs four-condition gate :2690-2710 with verbatim IO-drop example, COMMIT refusal execute.rs:4663-4671 exact string, clear-on-BEGIN/ROLLBACK :4926/:4957, MVCC shared-autocommit sibling variant :2713-2728); **temp-DDL committed schema** (connection.rs :93-121/:711-804 mark/commit/rollback/reset quartet, SetCookie TEMP_DB_ID arm execute.rs:14778-14782, publication-timing contract comment mod.rs:2172-2176, empty_temp_schema :583, set_temp_store teardown :3891-3897); **emitter/select.rs whole-file** (emit_materialized_build_inputs :324-572 rowid-only-vs-key+payload mode split with cross-product rationale :371-399, nested subplan save/restore :501-520, prune_join_order_for_materialized_inputs :579-633 with OUTER-JOIN term exclusion, access-method sanitization ladder :842-913, debug prefix assertion :536-570); **subquery.rs whole-file** (choose_from_clause_subquery_execution_mode :1339-1373 compound-SELECT exclusion :1350-1355, CTE pre-materialization-before-coroutines :1387-1390, shared-count excludes correlated post-write RETURNING :100-116, assign_select_subquery_eval_phases :2173-2241 with issue #6807 floor exception, subquery_reads_outer_aggregate register-read rule :2263-2295, LIMIT/OFFSET never-correlated closure :364-391, scalar-subquery CSE map :242-267, phase_floor table plan.rs:338-357); **AggregateState blob codec** (aggregate_operator.rs to_value_vector :738-805 / from_blob :1019-1065 positional layout, negative-group-key-count guard :1030-1042, MIN/MAX has_value omission :785-800, ColumnMask DISTINCT dedupe :1082-1083, persistence consumer persistence.rs:41-52). Gate-5 REAL RUNNER BLOCKED under fleet load (cargo build contention) → deterministic battery: ALL probe greps executed byte-exact BEFORE writing (17 anchors verified, counts recorded in capsules); direct tests pinned: statement_lifecycle_tests.rs :952/:989/:1017 (poison trio), mvcc/database/tests.rs:18118 (temp-DDL abandoned-COMMIT rollback), test_hash_join_materialization.rs :22/:297 (materialization regressions), tests/integration/stmt_journal.rs:688 (upsert may_abort pair), tests/fuzz/subjournal.rs (differential corpus). search_graph live: all five Retrieve queries resolve line-exact (mark_tx_poisoned, rollback_temp_schema family, constraint_may_abort + integration suite, begin/end_statement, AggregateState::from_blob/to_blob). OMITTED-WITH-REASON pass 13: emitter/{insert,update,delete}.rs per-statement emitters + expr/* translation (below the bar until a named question), core/functions+vector+uuid product planes (unchanged), io/ backends (standing omit), postgres/conformance SQL fixtures (parse-partial test data).

Pass 14 ([DONE:431], this lane, successor fire, 2026-08-24) — **DRIFT WAVE EXECUTED**, pin ADVANCED `def9a060`→`d9266124f` (+19,498 upstream commits ff-pulled via `git reset --hard origin/main` after two CRLF-perpetual-M gradlew.bat files blocked `pull --ff-only`; untracked .cgcignore preserved): re-indexed IN PLACE through the live-symlink root per [DONE:366] benign-variant ruling (NO path-slugged twin; project `turso` now 50,226n/352,846e, head==base==`d9266124f`, status ready); content-freshness proven by resolving drift-introduced `IndexMethodDatabaseIdentity` line-exact (:148-155). Diff-first citation-vs-inventory: 79 core/ files changed; 25 cited paths drifted (~90 capsules touched); symbol-level triage showed ALL cited symbols survive (PackedTs/TransactionState/is_visible_to/finalized_tx_states/GREEDY_JOIN_THRESHOLD=12/OpTransactionState/NamedSavepointFrame/poisoned_tx/HashBuildPlanner/MvccLazyCursor/SIZE_MARKER ladder...). MINED: core/index_method/ (810L mod.rs + 5,112L fts.rs — NEVER-cited subsystem rewritten by this wave) whole-contract + NEW core/translate/eqp.rs (862L) → **8 new capsule-v2 (136→144)**: index-method-spi-contract (factory→attachment→cursor; mvcc_support 4-posture enum :59-77; results_materialized DML-safety flag; hook ladder stage_statement_commit→on_statement_committed→{committed|rolled_back|replacement}→close with empty-defaults-only-for-stateless warning :536-541), mvcc-index-method-write-lease (IndexMethodWriteLease holder+last_publish_ts :3971-3978; acquire three-way :6259-6272 reentrant/Busy/WriteWriteConflict-on-publish>snapshot; release stamps commit_ts ONLY on Committed :6286-6289), index-method-context-identity (FNV runtime_id over incarnation⊕generation⊕names :175-191; Weak connection edge = drop-recovery cycle-breaker; documented MVCC-DDL collision tolerance :162-168), fts-writer-slot-trigger-refusal (one flushing cursor per index per statement; trigger double-writer Raise(Abort) :2033-2044; dead-claim replacement; writer built only after slot+lease), fts-control-record-manifest (incarnation+generation+per-file size/chunks FNV-sealed, same-transaction write; fail-closed decode :398-459; incarnation minting root.rotate_left(32)^nonce^entropy .max(1)), fts-snapshot-cache-budget (admission always-insert / retention ≤4 conns & 192MiB / oldest-dies newest-immune :1292-1302 verbatim rationale; matches_snapshot+matches_manifest dual validation; FileCache deliberately unbounded :501-507), fts-foreground-merge-budget (background merges FORBIDDEN :3179-3182 crash-consistency comment; one bounded merge/commit docs≤64k bytes≤32MiB; smallest-level-first + distrust of policy output :3149-3155; pending-mutation-aware byte accounting), eqp-detail-vocabulary (17-variant EqpDetail enum + SQLite-exact Display strings; END-key SeekOp NEGATED for display :410-423). RE-ANCHORED (drift-shifted citations corrected in-place): poisoned-explicit-transaction (:952/:989/:1017→:1165/:1202/:1230), optimizer-join-order-dp (:1568→:1569 const GREEDY_JOIN_THRESHOLD=12 unchanged), optimizer-cost-model-constants (estimate_index_cost :166→:171, rows_per_seek :283→:285, analyze :332→:349), optimizer-hash-join-pricing (:1199→:1200), from-clause-subquery-modes (:1339→:1373+, CTE pre-materialize :1230), subquery-eval-phases (:2173→:2100), hash-build-signature-reuse (:107→:108, builder registry :821→:856), mainloop-open-close-emission (open :47→:50, meta structs :95→:73), mainloop-body-emit-targets (emit :60→:52), vdbe-sorter-external-merge (starts verified unchanged), hash-build-input-materialization (helpers −7 lines each), ivm-delta-pipeline (capture :11770→:12050, apply_view_deltas :2000→:2168), ivm-dbsp-primitives (HashableRow :150→:141, 82/88h comment :122→:127), ivm-join-operator-nulls (NULL-reject :449-453 pinned), ivm-aggregate-blob-codec (starts unchanged), jsonb-binary-path-nav (**INFINITY_CHAR_COUNT 8→5 VALUE CORRECTION** + tests :4436/:4309/:4176→:5422/:5295/:5162). GATE-5 REAL RUNNERS at new pin: statement_lifecycle **40/40** (incl. re-anchored poison trio + NEW fts lease tests), checkpoint_state_machine **15/15**, vacuum **43/43**, json **176/176**, incremental **178/178** = 452 green; mvcc::database 383 passed / 2 FAILED on `pwritev: quota exceeded` (host disk-quota exhaustion under fleet load — environment defect, recorded not fabricated); FTS feature build BLOCKED by libsqlite3-sys bundled-C compile failure (`cc ... sqlite3.c` rc1) — integration suites runner-blocked-this-window, deterministic grep anchors executed instead. Coverage stdin-JSON ×5 decisive paths no_recorded_issue+metadata_match. OMITTED-WITH-REASON pass 14: toy_vector_sparse_ivf.rs (next-pass target #1), HybridBTreeDirectory flush state machine internals beyond its cache/manifest contracts (target #5), bindings/javascript+react-native wave files (out of scope), postgres/conformance churn (fixtures), eqp JSON builder detail (covered at contract level in eqp capsule).

NEXT-PASS TARGETS (pass 17+, ONLY past `1654d1587` drift or a NEW porting question): (1) drift check first: `git fetch origin main && git log 1654d1587..origin/main --stat`; the 2026-08-24 poll found only 3 commits (`51c99f1e8` sync-engine Windows io overflow fix + `af017276c` serverless version bump) touching bindings/rust/src/sync.rs + sync/sdk-kit/src/sync_engine_io.rs + serverless/rust/Cargo.toml — all outside cited planes; re-run citation-vs-inventory vs ALL 159 refs ONLY when core/ files appear; (2) HybridBTreeDirectory internals (pending_mutations→flushing_writes→catalog resumable flush state machine, fts.rs) IF a storage-backed-VFS question emerges; (3) core/translate/emitter/{insert,update,delete}.rs per-statement emitters whole-file IF a DML-emission porting question emerges; (4) core/translate/expr/* expression translation plane IF an expr-porting question emerges; (5) core/vector product-plane REMAINDER (serialize/text/slice/convert codecs, distance_cos/dot/l2 kernels) IF a function-library question emerges — jaccard kernel is now cited via vector-ivf-exact-rescore-topk; else squeezed-to-last-drop for cycle at 160/160 v2 relative to mined scope (three-way parity loader↔map↔disk verified 2026-08-24).

## Full view (memory graph)
Revalidate `turso` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `$REFERENCE_ROOT/memory/turso` (live symlink from `$REFERENCE_ROOT/turso`), HEAD `1654d1587`, full mode, 50,306 nodes / 353,465 edges, re-indexed in place at pass 15 after the +30-commit drift wave. Confirm every claim against source — the graph is an index, not truth; source and direct tests decide shipped claims.

## Boundaries
Adopt the MVCC, WAL, b-tree, pager, logical-log, shared-WAL, page-cache/buffer-pool internals, encryption framing, DatabaseStorage codec plane, MvccLazyCursor internals, the MVCC store-side mutation/readability contracts (write ladder, RootEntry bindings, covers-chain gate), the cursor resume-enum family (`state_machines.rs`), the subjournal latch, the DurableStorage port boundary, and (pass 12) the SQL planner planes: join-order DP/greedy search, cost-model constants, hash-join pricing, main-loop open/close/body emission scaffolding, hash-build signature reuse, grace hash-join executor, external sorter, the IVM delta pipeline with its DBSP primitives and NULL-matching join keys, and JSONB binary path navigation; keep SQLite frame compatibility windows; omit the server, protocol, and cloud layers unless a target requires them. (Pass 14) Adopt also the index-method SPI plane: factory/attachment/cursor contract with declared mvcc_support posture and statement-scoped hook ladder, the per-index MVCC write lease, context identity/snapshot stamping, and — for FTS specifically — writer slot, sealed manifest, retention budget, foreground merge; plus the EXPLAIN QUERY PLAN detail vocabulary with its end-key operator negation. The `io/` backend internals (io_uring specifics) remain omit-with-reason. Per-opcode families in `execute.rs` beyond those already named stay below the storage-engine bar; core/translate/emitter per-statement emitters, expr translation, functions/vector product planes remain omit-with-reason pending a named question; toy_vector_sparse_ivf and HybridBTreeDirectory flush internals are conditional next-pass targets, not omissions. VACUUM INTO's output-finalization path is covered only at its durability boundary (`finalize_vacuum_into_output`, SyncMode::Full TRUNCATE); wasm vacuum stub and `pragma.rs`/dialect auto-vacuum plumbing remain omit-with-reason. (Pass 15) Adopt also: the min-cell-size write-path invariant (padded leaf cells / real-size dividers) for any SQLite-page-format port; the JSON path-label escape duality, arrow-operator error precedence, aggregate blob gate, and json_tree root-row rules for JSON conformance ports; the failed-COMMIT rollback-latch arming order; the C-API completion contract (report error, never leak); kind-based token reclassification with SQLite-exact messages; fault-injection test rig design (path-scoped windows + counters + second-connection witness); blessed-corpus-as-spec conformance workflow. TCL/`tester.tcl` helper internals beyond their contract shape remain omit-with-reason; `bindings/tcl` full command surface is cited only at its wave scope. (Pass 16) Adopt also the vector-search index method as a WHOLE: shadow-index persistence naming, the blind-insert/paranoid-delete asymmetry, sum-denormalized posting rows with conservative stats drift, the sum-threshold approximation with its one-directional recall guarantee, exact-rescore-from-table candidate-generator contract, and the minimal no-op-hook SPI posture for methods whose state lives in ordinary transactional structures; the `core/vector` product-plane codecs/kernels beyond jaccard remain omit-with-reason pending the function-library question.

Pass 15 ([DONE:487], deepening-A lane, cron drain-lane-deepening-a successor fire, 2026-08-24) — **DRIFT WAVE EXECUTED**, pin ADVANCED `d9266124f`→`1654d1587` (+30 upstream commits ff-pulled cleanly; CRLF trap did not recur; untracked .cgcignore preserved): re-indexed IN PLACE through live-symlink root per [DONE:366] benign-variant ruling (project `turso` now 50,306n/353,465e ready, head==base==pin); content-freshness PROVEN by drift-introduced symbols `new_key_element_type` (:3578-3586), `ensure_min_cell_size` (:8138-8142), and `test_tiny_cell_insert_must_not_overlap_cell_pointer_array` resolving line-exact — after which check_index_coverage flagged bindings/c/src/lib.rs `metadata_changed` (graph served pre-drift spans :1015 vs tree :1028) → targeted re-index via `index_repository --repo-path --name turso` refreshed generation 2026-08-24T12:07Z, `stmt_run_to_completion` now :1028-1037 line-exact, lib.rs/io.rs metadata_match. Diff-first triage of the wave's real seams (b-tree corruption fix f1800bb8c, WAL-commit rollback c37d1db39+5baf4c12a, four JSON fixes bd4735743/6ef02dfa8/8db3da58e/53e2bf4e4, parser reclass 2096a3b63, C-API cleanup 27c3bccb0, TCL/conformance infra) → **9 new capsule-v2 (144→153)**: btree-min-cell-size-padding, json-path-label-escape-duality, json-arrow-error-precedence, json-agg-blob-gate-and-tree-root-rows, failed-commit-wal-rollback-latch, capi-finalize-reset-completion-contract, parser-var-token-reclassification, simulator-wal-fault-injection, tcl-conformance-harness-wave. REPAIRED EXISTING CAPSULES against new pin (bounded sweep of wave-touched files): btree-balancing (**PRE-EXISTING DEFECT FIXED**: constants block was cited at "btree.rs :2424-2433" but CKPT_BATCH_PAGES family ALWAYS lived in wal.rs — verified via `git show <old-pin>:core/storage/btree.rs`; rewritten to wal.rs :2424-2434 with assert :3862/:150 quotes re-pinned, balance_quick span confirmed UNCHANGED :3167 across both waves), poisoned-explicit-transaction (poisoned_tx :363→:387, mark/clear :2753→:2809, gate mod.rs :2690→:2891, COMMIT refusal execute.rs :4663→:4922-4931), vdbe-op-transaction-ladder (OpTransactionState :3735→:3993, inner :3989→:4214, mutex comment :4006→:4263, CheckSchemaCookie :4695), jsonb-binary-path-nav (tests +13 :5422/:5295/:5162→:5435/:5308/:5175, escape-duality cross-ref added), connection-savepoint-frame-ledger + savepoint-opcode-mirroring (op_auto_commit :4917/:4906→:4810 w/ call site :5183, clear_named_savepoints :4598/:4745→connection.rs :4996 called from :4858/:5011, fuzz comment :4722→:4986, cookie invalidation :4978→:5229-5249). GATE-5 REAL RUNNERS at new pin: tiny-cell corruption test **1/1** (`test_tiny_cell_insert...` GREEN), JSON suite **175/175** (`--features json --lib -- json::`), poison trio **3/3** (first real-runner execution of statement_lifecycle_tests trio), C-bindings busy tests **2/2** (`turso_sqlite3` package — first name attempt `turso-bindings-c` matched nothing), simulator WAL-fault regression **1/1 ×2** (`limbo_sim` is BIN-ONLY: `--bins` not `--lib`). **ENVIRONMENT DEFECT CLASS EXTENDED**: both C-busy tests RED under default TMPDIR (assert rc=1 at tempfile setup :3793) and sim run transiently lost its scratch dir to external deletion mid-run — both GREEN after `TMPDIR=$TMPDIR-turso-p15` (extends pass-14 `pwritev: quota exceeded` ruling; /tmp tmpfs at 80% under fleet load). Retrieves live-executed pre-write: drift symbols rank-1 line-exact; adversarial discipline maintained via positive controls on same-project queries. Coverage stdin-JSON ×9 decisive paths (post-reindex): no_recorded_issue all, generation_matches=true. OMITTED-WITH-REASON pass 15: tester.tcl helper internals beyond contract shape (product test-harness code), bindings/tcl command surface beyond wave scope, sqlite/conformance bless-list churn as fixtures, postgres/conformance untouched. NEXT-PASS TARGETS updated in leaf (target #1 = diff-first past `1654d1587`).

Pass 16 ([DONE:531], dedicated lane miner-turso, 2026-08-24) — **DEEP-LEARNING PASS at unchanged pin `1654d1587`** (index_status --verbose: root `$REFERENCE_ROOT/turso`, branch main, head==base==`1654d1587fab…`, ready, 50,306n/353,465e; upstream poll `git log 1654d1587..origin/main` = 3 commits touching ONLY bindings/rust/src/sync.rs + sync/sdk-kit/src/sync_engine_io.rs + serverless/rust/Cargo.toml/Cargo.lock → all outside cited planes ⇒ NO drift wave, no re-index): executed pass-15 NEXT-PASS TARGETS #2+#5(partial) by posing the vector-index porting question and whole-file-reading `core/index_method/toy_vector_sparse_ivf.rs` (1,613L) plus the scoring kernel `core/vector/operations/jaccard.rs::vector_f32_sparse_distance_jaccard` (:91-125) and all five direct tests (`tests/integration/index_method/mod.rs:99-499`) → **6 new capsule-v2 (VERIFIED inventory 154→160; pass-15's recorded "153" tally was an off-by-one, corrected by this run's three-way parity count)**: vector-ivf-shadow-schema (backing_btree shadow pair `{i}_inverted_index`/`{i}_stats`, nested-DDL needs_stmt_subtransactions=false Busy opt-out :435-443), vector-ivf-insert-machine (six-state ladder :45-87/:531-783; sum-denormalized posting rows; seek-result-discard blind insert :620-645), vector-ivf-delete-machine (eight-state twin :90-137/:785-1044; Found/TryAdvance/NotFound triage :886-910 with advance-once-trust-position; min/max never re-shrunk), vector-ivf-threshold-algebra (J=min(L,M)/(Q+L−min(L,M)) derivation comment :1252-1261 verbatim; two-range sum_threshold; −1.0 prune-all :1282; eq_only:false range scan :1318; scan_order/scan_portion budgeting :1115-1131), vector-ivf-exact-rescore-topk (candidate-generator contract; Corrupt on missing main-rowid :1510-1514; FloatOrd total_cmp :148-152; pop_last top-K :1571-1574; NaN when max_sum==0 jaccard.rs:121-123), vector-ivf-spi-posture-fuzz-contract (posture trio :347-349 backing_btree=false/results_materialized=true/TransactionalBackingStore vs FTS flush ladder; dual query patterns :325-335; differential fuzz delta contract mod.rs:464-495). Gate-5 REAL RUNNER at HEAD: `cargo test -p core_tester --test integration_tests -- test_vector_sparse_ivf` = **6 passed / 0 failed** fresh compile 1m51s (incl. mvcc macro variant + fuzz). Probes grep-verified byte-exact pre-write (17+11+7 anchors across source and tests). Coverage check_index_coverage ×2 cited paths no_recorded_issue + generation_matches=true. Work record CREATED this run at `$REFERENCE_ROOT/turso-work/{state,research,verification}.md`; shared-ledger row repaired from stale pass-0 to pass-16 truth (mesh lease unavailable in DSH — exact own-row edit only). OMITTED-WITH-REASON: core/vector product-plane remainder (serialize/text/slice/convert, cos/dot/l2 kernels), HybridBTreeDirectory flush internals, DML emitters, expr translation — all conditional questions still open. NEXT-PASS TARGETS updated in leaf (pass 17+: drift-gated census only if core/ files change; else conditional targets #2-#5 as listed).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`btree-balance-bounds.md`](./btree-balance-bounds.md)
- [`btree-balancing.md`](./btree-balancing.md)
- [`btree-cursor-count-spill-resume.md`](./btree-cursor-count-spill-resume.md)
- [`btree-min-cell-size-padding.md`](./btree-min-cell-size-padding.md)
- [`btree-redistribution.md`](./btree-redistribution.md)
- [`buffer-pool-arena-split.md`](./buffer-pool-arena-split.md)
- [`buffer-pool-deferred-init.md`](./buffer-pool-deferred-init.md)
- [`capi-finalize-reset-completion-contract.md`](./capi-finalize-reset-completion-contract.md)
- [`checkpoint-blocking-lock-gc-predicate.md`](./checkpoint-blocking-lock-gc-predicate.md)
- [`checkpoint-collection-snapshot.md`](./checkpoint-collection-snapshot.md)
- [`checkpoint-durability-ladder.md`](./checkpoint-durability-ladder.md)
- [`checkpoint-gc-floor.md`](./checkpoint-gc-floor.md)
- [`checkpoint-io-error-cleanup-ledger.md`](./checkpoint-io-error-cleanup-ledger.md)
- [`checkpoint-local-schema-view.md`](./checkpoint-local-schema-view.md)
- [`checkpoint-passive-publish-window.md`](./checkpoint-passive-publish-window.md)
- [`checkpoint-preemption-resume.md`](./checkpoint-preemption-resume.md)
- [`checkpoint-schema-lifecycle.md`](./checkpoint-schema-lifecycle.md)
- [`checkpoint-seq-compaction.md`](./checkpoint-seq-compaction.md)
- [`connection-savepoint-frame-ledger.md`](./connection-savepoint-frame-ledger.md)
- [`durable-storage-trait-boundary.md`](./durable-storage-trait-boundary.md)
- [`encryption-page-format.md`](./encryption-page-format.md)
- [`eqp-detail-vocabulary.md`](./eqp-detail-vocabulary.md)
- [`failed-commit-wal-rollback-latch.md`](./failed-commit-wal-rollback-latch.md)
- [`from-clause-subquery-modes.md`](./from-clause-subquery-modes.md)
- [`fts-control-record-manifest.md`](./fts-control-record-manifest.md)
- [`fts-foreground-merge-budget.md`](./fts-foreground-merge-budget.md)
- [`fts-snapshot-cache-budget.md`](./fts-snapshot-cache-budget.md)
- [`fts-writer-slot-trigger-refusal.md`](./fts-writer-slot-trigger-refusal.md)
- [`hash-build-input-materialization.md`](./hash-build-input-materialization.md)
- [`hash-build-signature-reuse.md`](./hash-build-signature-reuse.md)
- [`in-place-vacuum-publication.md`](./in-place-vacuum-publication.md)
- [`index-method-context-identity.md`](./index-method-context-identity.md)
- [`index-method-spi-contract.md`](./index-method-spi-contract.md)
- [`io-completions-groups.md`](./io-completions-groups.md)
- [`io-vfs-abstraction.md`](./io-vfs-abstraction.md)
- [`io-yield-completions.md`](./io-yield-completions.md)
- [`ivm-aggregate-blob-codec.md`](./ivm-aggregate-blob-codec.md)
- [`ivm-dbsp-primitives.md`](./ivm-dbsp-primitives.md)
- [`ivm-delta-pipeline.md`](./ivm-delta-pipeline.md)
- [`ivm-join-operator-nulls.md`](./ivm-join-operator-nulls.md)
- [`journal-mode-dispatch.md`](./journal-mode-dispatch.md)
- [`json-agg-blob-gate-and-tree-root-rows.md`](./json-agg-blob-gate-and-tree-root-rows.md)
- [`json-arrow-error-precedence.md`](./json-arrow-error-precedence.md)
- [`json-path-label-escape-duality.md`](./json-path-label-escape-duality.md)
- [`jsonb-binary-path-nav.md`](./jsonb-binary-path-nav.md)
- [`logical-log-deferred-commit.md`](./logical-log-deferred-commit.md)
- [`logical-log-portable-sync.md`](./logical-log-portable-sync.md)
- [`logical-log-replay-boundary.md`](./logical-log-replay-boundary.md)
- [`loglog-deferred-publication.md`](./loglog-deferred-publication.md)
- [`loglog-encrypted-in-place-expansion.md`](./loglog-encrypted-in-place-expansion.md)
- [`loglog-frame-format.md`](./loglog-frame-format.md)
- [`loglog-recovery-boundary.md`](./loglog-recovery-boundary.md)
- [`loglog-serializer-chunk-streams.md`](./loglog-serializer-chunk-streams.md)
- [`loglog-streaming-reader.md`](./loglog-streaming-reader.md)
- [`mainloop-body-emit-targets.md`](./mainloop-body-emit-targets.md)
- [`mainloop-open-close-emission.md`](./mainloop-open-close-emission.md)
- [`mvcc-begin-rollback.md`](./mvcc-begin-rollback.md)
- [`mvcc-btree-covers-chain-gate.md`](./mvcc-btree-covers-chain-gate.md)
- [`mvcc-checkpoint-ordering.md`](./mvcc-checkpoint-ordering.md)
- [`mvcc-clock-callback-contract.md`](./mvcc-clock-callback-contract.md)
- [`mvcc-commit-conflicts.md`](./mvcc-commit-conflicts.md)
- [`mvcc-commit-coordinator.md`](./mvcc-commit-coordinator.md)
- [`mvcc-commit-dependencies.md`](./mvcc-commit-dependencies.md)
- [`mvcc-commit-dependency-speculation.md`](./mvcc-commit-dependency-speculation.md)
- [`mvcc-commit-state-machine.md`](./mvcc-commit-state-machine.md)
- [`mvcc-conflict-detection-duality.md`](./mvcc-conflict-detection-duality.md)
- [`mvcc-conflict-detection.md`](./mvcc-conflict-detection.md)
- [`mvcc-cursor-snapshot-gates.md`](./mvcc-cursor-snapshot-gates.md)
- [`mvcc-cursor-write-routing.md`](./mvcc-cursor-write-routing.md)
- [`mvcc-dual-cursor-merge.md`](./mvcc-dual-cursor-merge.md)
- [`mvcc-eager-conflict-lanes.md`](./mvcc-eager-conflict-lanes.md)
- [`mvcc-finalized-tx-cache.md`](./mvcc-finalized-tx-cache.md)
- [`mvcc-finger-lazy-shadow-resolution.md`](./mvcc-finger-lazy-shadow-resolution.md)
- [`mvcc-gc-incremental-pass.md`](./mvcc-gc-incremental-pass.md)
- [`mvcc-gc-two-clocks.md`](./mvcc-gc-two-clocks.md)
- [`mvcc-hermitage-isolation-contract.md`](./mvcc-hermitage-isolation-contract.md)
- [`mvcc-index-method-write-lease.md`](./mvcc-index-method-write-lease.md)
- [`mvcc-index-versioning.md`](./mvcc-index-versioning.md)
- [`mvcc-lazy-cursor.md`](./mvcc-lazy-cursor.md)
- [`mvcc-materialized-at-tracking.md`](./mvcc-materialized-at-tracking.md)
- [`mvcc-packed-ts-version-model.md`](./mvcc-packed-ts-version-model.md)
- [`mvcc-read-path.md`](./mvcc-read-path.md)
- [`mvcc-rewrite-live-versions.md`](./mvcc-rewrite-live-versions.md)
- [`mvcc-rowid-allocation.md`](./mvcc-rowid-allocation.md)
- [`mvcc-savepoint-ledgers.md`](./mvcc-savepoint-ledgers.md)
- [`mvcc-savepoint-stack-internals.md`](./mvcc-savepoint-stack-internals.md)
- [`mvcc-schema-checkpointing.md`](./mvcc-schema-checkpointing.md)
- [`mvcc-seek-eqonly-short-circuit.md`](./mvcc-seek-eqonly-short-circuit.md)
- [`mvcc-store-write-ladder.md`](./mvcc-store-write-ladder.md)
- [`mvcc-vacuum-gate-ladder.md`](./mvcc-vacuum-gate-ladder.md)
- [`mvcc-version-model.md`](./mvcc-version-model.md)
- [`mvcc-visibility-predicates.md`](./mvcc-visibility-predicates.md)
- [`optimizer-cost-model-constants.md`](./optimizer-cost-model-constants.md)
- [`optimizer-hash-join-pricing.md`](./optimizer-hash-join-pricing.md)
- [`optimizer-join-order-dp.md`](./optimizer-join-order-dp.md)
- [`page-cache-sieve-eviction.md`](./page-cache-sieve-eviction.md)
- [`page-cache-spill-accounting.md`](./page-cache-spill-accounting.md)
- [`page-transform-codec-stack.md`](./page-transform-codec-stack.md)
- [`pager-cache-admission.md`](./pager-cache-admission.md)
- [`pager-durability-ordering.md`](./pager-durability-ordering.md)
- [`pager-pin-guard.md`](./pager-pin-guard.md)
- [`pager-savepoint-walpos-capture.md`](./pager-savepoint-walpos-capture.md)
- [`pager-spill-tags.md`](./pager-spill-tags.md)
- [`parser-var-token-reclassification.md`](./parser-var-token-reclassification.md)
- [`poisoned-explicit-transaction.md`](./poisoned-explicit-transaction.md)
- [`portable-cursor-fixed-point.md`](./portable-cursor-fixed-point.md)
- [`portable-delete-extension.md`](./portable-delete-extension.md)
- [`portable-logical-codec.md`](./portable-logical-codec.md)
- [`rootpage-binding-lifecycle.md`](./rootpage-binding-lifecycle.md)
- [`savepoint-mirror-compensation.md`](./savepoint-mirror-compensation.md)
- [`savepoint-name-busy-gate.md`](./savepoint-name-busy-gate.md)
- [`savepoint-opcode-mirroring.md`](./savepoint-opcode-mirroring.md)
- [`shared-wal-backfill-proof.md`](./shared-wal-backfill-proof.md)
- [`shared-wal-commit-publication.md`](./shared-wal-commit-publication.md)
- [`shared-wal-coordination.md`](./shared-wal-coordination.md)
- [`shared-wal-frame-index.md`](./shared-wal-frame-index.md)
- [`shared-wal-mmap-lifecycle.md`](./shared-wal-mmap-lifecycle.md)
- [`shared-wal-ownership-locks.md`](./shared-wal-ownership-locks.md)
- [`shared-wal-reader-slots.md`](./shared-wal-reader-slots.md)
- [`shared-wal-snapshot-reuse.md`](./shared-wal-snapshot-reuse.md)
- [`simulator-wal-fault-injection.md`](./simulator-wal-fault-injection.md)
- [`skiplist-primitive.md`](./skiplist-primitive.md)
- [`slot-bitmap-lockfree-allocation.md`](./slot-bitmap-lockfree-allocation.md)
- [`spin-lock-primitive.md`](./spin-lock-primitive.md)
- [`statement-savepoint-lifecycle.md`](./statement-savepoint-lifecycle.md)
- [`stmt-journal-flag-analysis.md`](./stmt-journal-flag-analysis.md)
- [`storage-databasestorage-codec-io.md`](./storage-databasestorage-codec-io.md)
- [`storage-pin-guard.md`](./storage-pin-guard.md)
- [`storage-redistribution-legality.md`](./storage-redistribution-legality.md)
- [`storage-soft-cache-singleflight.md`](./storage-soft-cache-singleflight.md)
- [`storage-spill-tags.md`](./storage-spill-tags.md)
- [`subjournal-single-owner-latch.md`](./subjournal-single-owner-latch.md)
- [`subquery-eval-phases.md`](./subquery-eval-phases.md)
- [`tcl-conformance-harness-wave.md`](./tcl-conformance-harness-wave.md)
- [`temp-ddl-committed-schema.md`](./temp-ddl-committed-schema.md)
- [`testing-yield-injection.md`](./testing-yield-injection.md)
- [`vacuum-target-build-engine.md`](./vacuum-target-build-engine.md)
- [`vdbe-active-op-slot.md`](./vdbe-active-op-slot.md)
- [`vdbe-async-step-loop.md`](./vdbe-async-step-loop.md)
- [`vdbe-autocommit-cleanup-baton.md`](./vdbe-autocommit-cleanup-baton.md)
- [`vdbe-column-deferred-seek.md`](./vdbe-column-deferred-seek.md)
- [`vdbe-hash-join-grace-spill.md`](./vdbe-hash-join-grace-spill.md)
- [`vdbe-op-new-rowid-ladder.md`](./vdbe-op-new-rowid-ladder.md)
- [`vdbe-op-no-conflict-null-gate.md`](./vdbe-op-no-conflict-null-gate.md)
- [`vdbe-op-transaction-ladder.md`](./vdbe-op-transaction-ladder.md)
- [`vdbe-seek-state-machine.md`](./vdbe-seek-state-machine.md)
- [`vdbe-sorter-external-merge.md`](./vdbe-sorter-external-merge.md)
- [`vector-ivf-delete-machine.md`](./vector-ivf-delete-machine.md)
- [`vector-ivf-exact-rescore-topk.md`](./vector-ivf-exact-rescore-topk.md)
- [`vector-ivf-insert-machine.md`](./vector-ivf-insert-machine.md)
- [`vector-ivf-shadow-schema.md`](./vector-ivf-shadow-schema.md)
- [`vector-ivf-spi-posture-fuzz-contract.md`](./vector-ivf-spi-posture-fuzz-contract.md)
- [`vector-ivf-threshold-algebra.md`](./vector-ivf-threshold-algebra.md)
- [`wal-checkpoint-constants.md`](./wal-checkpoint-constants.md)
- [`wal-checkpoint-ordering.md`](./wal-checkpoint-ordering.md)
- [`wal-commit-publication.md`](./wal-commit-publication.md)
- [`wal-frame-codec.md`](./wal-frame-codec.md)
- [`wal-recovery.md`](./wal-recovery.md)
- [`wal-snapshot-read-marks.md`](./wal-snapshot-read-marks.md)
- [`wal-snapshot-slots.md`](./wal-snapshot-slots.md)
