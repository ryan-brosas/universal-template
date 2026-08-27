---
name: appflowy-foundation
description: "Use when porting AppFlowy's offline-first sync kernels — assembling CRDT objects with disk persistence and cloud sync, routing typed events across an FFI boundary, running QoS background task queues, reconnecting realtime sockets, or implementing a local server that satisfies cloud traits without a backend."
---
# AppFlowy: local-first collaborative workspace foundation

## Use this for
Use when porting AppFlowy's offline-first sync kernels: assembling CRDT objects with disk persistence and cloud sync, routing typed events across an FFI boundary, running QoS background task queues, reconnecting realtime sockets, or implementing a "local server" that satisfies cloud traits without a backend. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/collab-builder-lifecycle.md` — build→domain-open→finalize assembly; plugin attach exactly once under lock.
- `references/collab-disk-persistence.md` — load-into-one-txn, flush_doc + explicit commit protocol.
- `references/document-lifecycle-two-maps.md` — documents/removing_documents graveyard with 120s delayed eviction.
- `references/document-cloud-open-fallback.md` — disk→cloud→RecordNotFound ladder; empty remote doc_state is 404, never a blank doc.
- `references/dispatch-event-map.md` — flat event map, duplicate-event startup panic, total error→response conversion.
- `references/dispatch-localset-runtime.md` — LocalSet-only dispatch contexts; handler panics become JoinError responses.
- `references/dispatch-handler-extraction.md` — Extract→Handle state machine; decode failures surface as success-shaped error responses.
- `references/priority-task-queue.md` — QoS-desc/id-desc max-heap (LIFO within a level), pop-time cancel, per-task timeout.
- `references/ws-reconnect-ladder.md` — state→action table with cancel-then-jitter reconnect ([min..10)s).
- `references/local-server-null-cloud.md` — offline mode answers wire-shaped queries from the KV store; typed refusals for the rest.
- `references/snowflake-id-generator.md` — 41|10|12 bit layout; panic-on-clock-backwards fail-fast policy.
- `references/instant-index-writer.md` — Weak-registry reaper loop feeding search consumers every 30s without owning docs.
- `references/ffi-byte-protocol.md` — length-prefixed port protocol; Rust leaks, Dart frees; one-thread LocalSet host.
- `references/core-composition-root.md` — single-strong-owner/Weak-everywhere wiring order for circular manager deps.
- `references/notification-bridge.md` — callback-vs-stream notification split; mpsc(1) profile-change coalescing.
- `references/workspace-identity-guard.md` — last-moment workspace-id check before any persisted write.
- `references/sync-kill-switch.md` — Option-typed client access sampled at accessor time; DataSyncRequired on disabled sync.

## Capsule map
- **Collab assembly** — `collab-builder-lifecycle`, `collab-disk-persistence`: spawn_blocking Yrs build with RocksDB plugin attached pre-load; flush = encode(sv+doc_state) then explicit commit; load errors log-not-fail inside one committed txn.
- **Document lifecycle** — `document-lifecycle-two-maps`, `document-cloud-open-fallback`: close parks the SAME Arc in a graveyard for 120s so reopen resumes in-flight sync; open falls back disk→cloud and deletes corrupt data on invalid-data errors; only sync-enabled opens enter the cache.
- **Event dispatch** — `dispatch-event-map`, `dispatch-localset-runtime`, `dispatch-handler-extraction`: one flat map keyed by stringified events (duplicates panic at startup); default features REQUIRE a LocalSet thread (dart-ffi owns it); extraction errors return as responses; handler panics launder into JoinError bodies.
- **Background tasks** — `priority-task-queue`, `instant-index-writer`: UserInteractive preempts Background; within a level highest-id-first LIFO (max-heap); cancel checked after dequeue; timeout marks state while the future finishes; Weak-registry reaper feeds search consumers without owning docs.
- **Realtime & offline** — `ws-reconnect-ladder`, `sync-kill-switch`, `local-server-null-cloud`: PingTimeout/Lost→jittered reconnect, Unauthorized→refresh-only, Refresh→reconnect, Invalid→disconnect; disabled sync = Option-typed client + typed error; LocalServer implements AppFlowyServer against the local KV store.
- **Identity & plumbing** — `snowflake-id-generator`, `workspace-identity-guard`, `ffi-byte-protocol`, `core-composition-root`, `notification-bridge`: panic-on-backwards snowflake ids; last-moment workspace guard before writes; u32 big-endian length prefix on every FFI response; Arc-once/Weak-everywhere resolver ordering; callbacks for block changes vs spawned streams for state, mpsc(1) coalescing.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
AppFlowy (AGPL-3.0), `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory project `ext-appflowy` (root /mnt/hdd/utopia/inspo/external/appflowy, branch main, FULL mode, 78,018 nodes / 234,736 edges, generation 2026-08-23T11:38:37Z, head_sha == base_sha at pass 1; parse_partial ×48 confined to Flutter/platform-glue/migration files, none cited). AGPL note: porting this code into a distributed product triggers AGPL obligations — treat capsules as behavior specifications if license-incompatible.

## Full view (memory graph)
Revalidate `ext-appflowy` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Pass-1 evidence: stdin-JSON coverage of all 19 cited paths returned no_recorded_issue+metadata_match with generation_matches=true; BM25 retrieval rank#1 line-exact for every Retrieve query above; adversarial wrong-project queries (`plugin_map_or_crash AFPluginDispatcher`@ext-joplin, `AppFlowyCollabBuilder finalize`@ext-docmost, `IDGenerator wait_next_millis`@ext-meetily) each returned total:0.

## Boundaries
Adopt the behavioral contracts (assembly order, response-as-error channel, QoS/LIFO ordering, graveyard reopen, cancel-then-jitter reconnect, Weak registries); adapt codecs, storage engines, and trait shapes to your host; omit product surfaces — Flutter UI, flowy-database2 field/type-option internals, flowy-user auth flows, AI chat/local-LLM stack, server gateway socket.io choreography, wasm branches — which live outside these seams.
