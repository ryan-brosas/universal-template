---
name: affine-foundation
description: "Use when porting CRDT sync loops, offline-first storage ladders, or block-editor data layers — AFFiNE local-first collaboration stack: Yjs sync engine (DocEngine/SyncPeer), reactive block store (stash/pop, flat Y.Map proxies, schema globs), and production doc-sync job kernel with clock-map dedup."
---

# AFFiNE: local-first collaborative block editor

## Use this for
Use when porting CRDT/OT-adjacent sync engines (Yjs update push/pull loops, echo guards, retry ladders), offline-first storage rungs (IndexedDB → BroadcastChannel → server), reactive block-editor stores over Yjs, schema-globbed parent/child validation, stash/pop optimistic UI edits, or server-side snapshot squashing of update streams. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/doc-source-contract.md` — the three-method storage contract (pull/push/subscribe) every backend must honor.
- `references/sync-peer-state-machine.md` — SyncPeer's three concurrent loops and the origin-name echo guard.
- `references/doc-engine-peer-lifecycle.md` — main-before-shadow startup ordering and push-drained graceful stop.
- `references/priority-queue-shared-target.md` — abortable wake-up queues with dequeue-time priority rules.
- `references/local-first-source-impls.md` — IndexedDB row compaction + BroadcastChannel init/update handshake.
- `references/blob-engine-shadows.md` — content-addressed blob replication: await main, fanout shadows, list-diff sweep.
- `references/y-block-encoding.md` — sys:/prop: wire format, parent-side child ordering, root discovery scan.
- `references/schema-validation-glob.md` — bidirectional minimatch + @role matching over parent/children allowlists.
- `references/store-islocal-heuristic.md` — the four-clause isLocal classification duplicated across four observers.
- `references/sync-controller-stash-pop.md` — prop-level optimistic edits that bypass Yjs until popped.
- `references/reactive-proxy-loop.md` — createYProxy loop-breaker trio: proxy:true origin tags, WeakMap registry, intercepted array methods.
- `references/flat-native-y-map.md` — dotted-path keys in one flat Y.Map; prefix-sweep deletes; single-transaction subtree writes.
- `references/text-delta-ops.md` — delta-preserving join, delete-the-tail split, CRLF normalization.
- `references/boxed-native-wrapper.md` — tagged-Y.Map atomic boxing for whole-value (non-merged) payloads.
- `references/move-blocks-contiguity.md` — multi-block move preconditions, contiguity throw, insert-index drift rule.
- `references/doc-sync-peer-jobs.md` — production DocSyncPeer: five job types, fixed drain order, three-clock metadata, terminal permission errors.
- `references/server-snapshot-squash.md` — read-time squash into snapshots with timestamp-guarded upsert and fail-open native validation.
- `references/awareness-broadcast-source.md` — ephemeral presence sync: 'remote' origin convention, announce-on-connect handshake.
- `references/transformer-error-capture-funnel.md` — swallow-and-log funnel + zod gates at both ends of every doc/slice/block conversion.
- `references/transformer-flatten-insert-pipeline.md` — flatten→serial-convert→rebuild tree, DFS pre-order root rule, nextTick yield every 100 inserts.
- `references/transformer-slice-move-vs-insert.md` — temporary-root envelope; hasBlock(first.id) fork between moveBlocks and insert; parent-required throw on the move path.
- `references/transformer-per-flavour-hook.md` — schema.transformer?.() with BaseBlockTransformer fallback; version −1 sentinel for unversioned snapshots.
- `references/transformer-tagged-json-roundtrip.md` — `$blocksuite:internal:text$` / `:native$` envelopes; Reflect.has revival; Text rides as delta.
- `references/transformer-assets-manager-ladder.md` — File-rename/MIME-trust/octet-stream-sniff blob ladder; conflict renames the copy only.
- `references/transformer-middleware-slots.md` — four rxjs Subjects (before/after × import/export), payload unions with parent/index context, cleanup contract.
- `references/transformer-replace-id-middleware.md` — six subscriptions over one closure idMap; before-assign ids, after-repair cells/deltas/refs/surface elements.
- `references/transformer-upload-middleware.md` — view-driven re-arm loop, abort race arm, sha-addressed blobs, withoutTransact undo-pollution guard.
- `references/transformer-base-adapter-template.md` — BaseAdapter template method + wrapFakeNote synthetic note + unclosed-nodes throw in ASTWalker.walk.
- `references/transformer-astwalker-context-stack.md` — openNode/closeNode stack attach into array props only; global vs per-node context lifetime.
- `references/transformer-astwalker-skip-protocol.md` — skipAllChildren vs skipChildren(n) resume semantics; per-visit flag resets are structural.
- `references/transformer-memory-blob-crud.md` — MemoryBlobCRUD sha-keyed dual-overload set; getAssetName naming ladder over the 38-entry MIME table.
- `references/transformer-doccrud-composition.md` — production wiring recipe: collection.blobSync + null-returning docCRUD.get + direction-specific middleware sets.
- `references/transformer-config-middlewares.md` — title→adapterConfigs map vs fileName→snapshot mutation: two distinct injection channels.
- `references/transformer-snapshot-schemas.md` — BlockSnapshot/DocSnapshot/SliceSnapshot zod shapes incl. recursive lazy children and backward-compat tags.

## Capsule map
- **Sync engine (`@blocksuite/sync`)**
  - `doc-source-contract`: pull must return diffUpdate(storage, callerStateVector); source.name doubles as echo marker.
  - `sync-peer-state-machine`: per-doc batching queues; `[0,0]` empty-update filter on both push and apply; retry resets ALL queues.
  - `doc-engine-peer-lifecycle`: shadow peers start only after main loads; graceful stop waits for pendingPushUpdates === 0.
  - `priority-queue-shared-target`: one SharedPriorityTarget reprioritizes all peer queues at dequeue time.
  - `local-first-source-impls`: append+compact rows (mergeCount=1 default); 'init' handshake answered by every listener.
  - `blob-engine-shadows`: sha-keyed blobs; delete intentionally a logged no-op until reference indexer exists.
  - `awareness-broadcast-source`: ephemeral presence; reply-to-connect carries own clientID only.
- **Reactive block store (`@blocksuite/store`)**
  - `y-block-encoding`: four sys: keys exactly; children ordered in PARENT's sys:children; root found by role scan (no back-pointer).
  - `schema-validation-glob`: BOTH sides' allowlists must agree via bidirectional minimatch/'@role' match.
  - `store-islocal-heuristic`: undo-manager origin ⇒ isLocal:true (surprising but load-bearing); remote applies must carry non-clientID origin.
  - `sync-controller-stash-pop`: stashed writes never touch yBlock; pop = unconditional overwrite (last-writer-wins).
  - `reactive-proxy-loop`: forgetting the {proxy:true} transaction tag = infinite observer loop.
  - `flat-native-y-map`: nested JS objects flatten to prop:a.b.c keys; prefix-sweep deletes share one transaction (atomic undo).
  - `text-delta-ops`: split deletes [index, END) and returns right part; join preserves OTHER's formatting via delta replay.
  - `boxed-native-wrapper`: '$blocksuite:internal:native$' type tag discriminates atomic boxes from deep-converted maps.
  - `move-blocks-contiguity`: selection contiguity throws BEFORE mutation; later source-parent groups shift insert index +1.
- **Production sync + server storage**
  - `doc-sync-peer-jobs`: connect/pullAndPush decision by persisted pushed/pulledRemote clocks vs live remote clock; DOC_ACTION_DENIED terminal per doc.
  - `server-snapshot-squash`: ON CONFLICT ... WHERE updated_at <= $ts makes concurrent snapshot writes idempotent; validation fails OPEN.
- **Transformer / adapter plane (`@blocksuite/store` transformer + shared adapters) — pass 2**
  - `transformer-error-capture-funnel`: every public conversion returns undefined on failure; zod parse runs in BOTH directions; only root/meta misses construct TransformerError.
  - `transformer-flatten-insert-pipeline`: DFS pre-order flatten is load-bearing (first flat entry = tree root); nextTick yield each 100 inserts keeps paste responsive.
  - `transformer-slice-move-vs-insert`: temporary-root envelope unifies top-level entries; hasBlock(first.id) ⇒ moveBlocks (parent REQUIRED) else insert.
  - `transformer-per-flavour-hook`: schemas carry optional custom transformers over a SHARED configs Map; version −1 = "no version recorded", not an error.
  - `transformer-tagged-json-roundtrip`: Text/Boxed revive via Reflect.has on `$blocksuite:internal:*$` tags; revived Text is a NEW Y.Text (compare deltas, not identity).
  - `transformer-assets-manager-ladder`: File→rename-copy-on-conflict, trusted MIME→store, octet-stream→dynamic file-type sniff; cleanup() preserves uploadingAssetsMap.
  - `transformer-middleware-slots`: page-level beforeImport precedes all block events; afterImport fires per block THEN per page — order is the idMap contract.
  - `transformer-replace-id-middleware`: assign ALL ids before import, repair cells/deltas/surface refs after; surface child forced last; missing connector ref THROWS.
  - `transformer-upload-middleware`: expect-id → view 'add' re-arm → sha store → withoutTransact prop write; abort arm resolves null; no retry.
  - `transformer-base-adapter-template`: wrappers own snapshot+error-capture, subclasses own format; wrapFakeNote guards double-wrap by head-flavour check.
  - `transformer-astwalker-context-stack`: closeNode pushes child into parent's ARRAY prop only; node context dies with its frame — promote to global before pop.
  - `transformer-astwalker-skip-protocol`: skipAllChildren prunes subtree but still runs leave; skipChildren(n) resumes mid-list and must reset per visit.
  - `transformer-memory-blob-crud`: reference blob stub + getAssetName ladder (verbatim name > name+ext > blobId.ext); unknown blobId throws.
  - `transformer-doccrud-composition`: fresh Transformer per operation; docCRUD.get returns null for exists-elsewhere checks; middleware sets differ import vs export.
  - `transformer-config-middlewares`: title registry via config map vs fileName via snapshot mutation — two channels, do not unify.
  - `transformer-snapshot-schemas`: discriminated literals + recursive lazy children + required numeric createDate; tags kept empty for backward compat.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
AFFiNE (MIT for blocksuite/* and most packages/*; EE license carve-out for packages/backend/server + packages/common/native — noted per-capsule), `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine` (FULL mode, generation 2026-08-23T11:37:23Z, 136,046 nodes / 409,043 edges, head==base b530198a; parse_partial mostly SQL/scss/helm noise; check_index_coverage no_recorded_issue on all 23 cited paths). Pass 2 (2026-08-24, same pin, zero drift) added the transformer/adapter plane: check_index_coverage no_recorded_issue on all 10 newly cited paths (generation_matches=true); direct tests `framework/store/src/__tests__/{transformer,assets}.unit.spec.ts` executed GREEN 10/10 via repo vitest.

## Full view (memory graph)
Revalidate `ext-affine` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/affine`, branch canary at b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a, full mode, 136k nodes / 409k edges, indexed 2026-08-23. search_graph BM25 resolves symbols line-exact across blocksuite/framework/{sync,store} and packages/common/nbstore (verified: SyncPeer.sync, DocEngine.start callers_total=0 [entry-point], DocCRUD.addBlock, docDiffUpdate total=1, ClockMap.setIfBigger). Pass 2 verified the transformer/adapter retrieval plane line-exact: Transformer._insertBlockTree (transformer.ts:522-569), ASTWalkerContext.{openNode,closeNode,skipChildren,cleanGlobalContextStack} (context.ts), AssetsManager.readFromBlob + makeNewNameWhenConflict (transformer/assets.ts:61-92/:10-19), replaceIdMiddleware (replace-id.ts:21-256), uploadMiddleware (upload.ts:12-118), BaseAdapter.fromSlice/toSlice/wrapFakeNote (adapter/base.ts), ASTWalker.walk/_visit. Source and direct tests decide shipped claims; nbstore has upstream vitest specs under src/__tests__ (sync.spec.ts) while framework sync has only queue/blob specs; framework/store adds transformer+assets unit specs (executed green pass 2).

## Boundaries
Adopt pure contracts: the DocSource interface, echo-guard conventions, queue wake-up pattern, Yjs wire encoding, guarded upsert, snapshot zod shapes, tagged JSON envelopes, middleware slot lifecycle, ASTWalker open/close protocol. Adapt host-specific integration: transports (BroadcastChannel/socket.io), persistence engines (IndexedDB/Postgres), signal/rxjs event surfaces, blob stores behind BlobCRUD. Omit product behavior: AFFiNE cloud workspace semantics, permission service internals beyond the error-name taxonomy, EE-licensed server code itself (the CONTRACT ports; the code may not under its license).
