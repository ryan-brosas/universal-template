---
name: docmost-foundation
description: 'Use when porting docmost''s realtime collaboration kernel: Redis-synced multi-instance Yjs routing, WS auth ladders, debounced CRDT-to-SQL persistence, and page-tree permissions.'
---

# docmost: realtime collaboration kernel

## Use this for
Use when building or porting multi-instance collaborative editing (Yjs/hocuspocus-style), WebSocket auth + read-only enforcement, CRDT↔relational persistence with history/versioning throttles, server-side Yjs mark surgery, or hierarchical page ACLs. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/dual-plane-gateway.md` — one WS entrypoint switching between standalone hocuspocus and the Redis proxy plane without double-handling frames.
- `references/redis-doc-lock-claim.md` — atomic `SET PX NX GET` claim + half-TTL heartbeat electing a single merge authority per document.
- `references/socket-proxy-relay.md` — relaying a client's byte stream to a remote owner over pub/sub while keeping one physical socket.
- `references/custom-event-rpc.md` — request/response remote mutation (`customEventStart/Complete`, replyId + TTL) against whichever server owns a doc.
- `references/ws-auth-readonly-ladder.md` — collab-JWT verification through space role, page restriction, and deleted-page readOnly decisions.
- `references/page-tree-permission-sql.md` — one recursive CTE answering traversal access AND nearest-restricted-writer edit rights, failing closed.
- `references/debounced-store-pipeline.md` — the exact save order (JSON + binary + text) with deep-equal no-op gating of every side effect.
- `references/contributor-attribution.md` — drain-on-read editor sets handed across processes via Redis for contributor credit.
- `references/history-throttle.md` — deduped delayed queue job producing at-most-one snapshot per quiet window, fast path for young pages.
- `references/yjs-mark-surgery.md` — RelativePosition-based comment marks applied directly on Y.XmlText, bypassing updateYFragment.
- `references/json-ydoc-ladder.md` — hydration precedence (live > DB binary > legacy JSON > fresh) and safe replace/append/prepend mutations.
- `references/unknown-node-stripping.md` — rendering docs from newer schemas by unwrapping unknown nodes instead of crashing.
- `references/client-socket-refcount.md` — SPA-wide shared collab socket with grace-period disconnect on last release.
- `references/collab-process-topology.md` — separate realtime process bootstrap plus flush-before-exit shutdown choreography.

## Capsule map
- **Connection plane** — `dual-plane-gateway`: serializeRequest whitelist + WsSocketWrapper write-side wrapper; events flow through exactly ONE pipeline. `client-socket-refcount`: acquire/release with 5s grace so route changes never drop live sessions. `collab-process-topology`: `/collab` upgrade path adapter, stats gate, closeConnections → flushPendingStores → afterUnloadDocument latch before exit.
- **Cluster sync kernel (redis-sync)** — `redis-doc-lock-claim`: `<prefix>Lock:<doc>` key holds owner id; losers read winner via GET option; crash visibility bounded by lockTTL. `socket-proxy-relay`: origin/owner split with CollabProxySocket; ConnectionTimeout closes are never relayed; proxied connections need manual liveness refresh. `custom-event-rpc`: replyId-correlated start/complete envelope with TTL rejection; `onlyIfOpen` reads without claiming.
- **Auth & permission plane** — `ws-auth-readonly-ladder`: deny → restricted-readOnly → space-reader-readOnly → deleted-readOnly; dedicated COLLAB JWT audience. `page-tree-permission-sql`: recursive ancestors CTE; `bool_and` fail-closed traversal; nearest restricted ancestor's writer role wins via ordered array_agg with NULLS LAST.
- **Persistence & history plane** — `debounced-store-pipeline`: three derived artifacts per save inside a row-locked tx; page=null sentinel gates broadcast/transclusions/queues/history. `contributor-attribution`: onChange-tagged users drained once per flush, re-added to Redis for the async history worker. `history-throttle`: `jobId: page.id` dedupe + age-selected delay (1min if page <5min old else 5min); processor re-checks content equality and restores popped contributors on failure.
- **Yjs content surgery** — `yjs-mark-surgery`: JSON RelativePositions resolve against current doc (null ⇒ throw); tag-counting offset walk; codeBlock exempt; removal is format-with-null. `json-ydoc-ladder`: isEmpty guard prevents stale JSON resurrecting over newer CRDT state; replace = delete-range then apply foreign update. `unknown-node-stripping`: only "Unknown node type" RangeError triggers unwrap recursion that flattens known grandchildren upward.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
docmost (AGPL-3.0), `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory project `ext-docmost` (ready FULL, head==base==pin, 25,966n/51,981e, gen 2026-08-23T11:44:55Z, generation_matches=true). Coverage: check_index_coverage on all 20 cited paths = no_recorded_issue+metadata_match except `page-permission.repo.ts` flagged partial (tree-sitter ranges near line 399) — that capsule cites source lines read directly at the pin. parse_partial ×17 repo-wide = CSS modules + 2 spec/helpers files + the permission repo; none cited except as noted.

## Full view (memory graph)
Revalidate `ext-docmost` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: lock-claim election, proxy relay envelopes, RPC correlation, auth decision order, CTE permission semantics, store ordering, throttle keys, RelativePosition handling. Adapt host-specific integration: Nest providers, BullMQ queues, ioredis/msgpackr, tiptap extension list, kysely SQL dialect. Omit product behavior: docmost UI, EE features, specific queue job payloads, transclusion domain logic beyond the sync hook contract.
