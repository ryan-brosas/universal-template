<!-- capsule-v2 -->
# Pagination & caching rules — how do clients page long lists, and when may a response be cached?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6e3588efb46e7542d98498e5c630a0a86`; Codebase Memory `modelcontextprotocol`. **Question:** What are the exact cursor-discipline and cacheability rules (`ttlMs`/`cacheScope`) for list and read results, including their interaction with MRTR and notifications?

## Opaque cursors + TTL/scope hints with hard exclusions
**Path/Symbol:** `schema/draft/schema.ts` — shared list envelope :1054–1110 (request `cursor?`, result `nextCursor?` + `ttlMs` + `cacheScope: "public"|"private"` via `CacheableResult`); prose: `docs/specification/draft/server/utilities/pagination.mdx` + `docs/specification/draft/server/utilities/caching.mdx` whole.
**Signature:** request `{ cursor?: string }` → result `{ resultType: "complete", …items, nextCursor?: string, ttlMs?: number, cacheScope?: "public"|"private" }`. Cacheable operations: `server/discover`, `tools/list`, `prompts/list`, `resources/list`, `resources/templates/list`, `resources/read`.
**Data Shape:** cursor = opaque string token (position in result set); page size is server-chosen; cache key = method + result-affecting params (`uri`, `cursor`).

### Decisive source
```md
<!-- pagination.mdx, Client MUSTs — the empty-string trap: -->
Clients MUST treat cursors as opaque tokens:
- Don't make assumptions about cursor format
- Don't attempt to parse or modify cursors
- Don't make any determination based on cursor value other than whether a
  non-null value was provided (e.g. an empty string is a valid cursor and
  thus MUST NOT be treated as the end of results)
Missing `nextCursor` = end of results. Invalid cursor => -32602 Invalid params.

<!-- caching.mdx, the two hard exclusions: -->
Interim results with `resultType: "input_required"` ... are not cacheable and
carry no caching hints.
Results produced by retrying a request through the [MRTR] mechanism — that is,
requests carrying `inputResponses` or `requestState` — MUST NOT be cached, as
they depend on inputs that are not part of the cache key.

<!-- caching.mdx, freshness ladder: ttlMs=0 => immediately stale; absent =>
assume 0; negative => ignore-and-treat-as-0; servers MUST send >= 0. A
received notification invalidates a still-fresh cached entry immediately. -->
```

**Flow:** first list request (no cursor) → server returns one page + optional `nextCursor`; client loops with returned cursor verbatim until `nextCursor` is missing → each PAGE is independently cached with its OWN `ttlMs` clock starting at that page's receipt → a matching change notification (`listChanged`) invalidates instantly → stale ⇒ re-fetch THAT page by cursor; invalid cursor ⇒ discard ALL cached pages and restart without cursor.
**Invariant:** cursors carry zero semantics to clients (empty string ≠ end); `cacheScope:"private"` forbids sharing across authorization contexts while `"public"` may leak through shared proxies even on authenticated endpoints — so access control can NEVER ride on `cacheScope`; servers MUST keep `cacheScope` uniform across all pages of one list; no cross-page consistency — snapshot-seekers re-fetch from page one; freshness math is `now < t_received + ttlMs`.
**Probe:** no runtime tests in the spec repo; machine anchors are the TS envelope types plus `schema/draft/examples/**` validated via `scripts/validate-examples.ts` (ListToolsResult family). Coverage caveat recorded honestly; envelope basics already pinned in schema-registration.md — this capsule adds the key/discipline/exclusion layer.

## Get live surrounding code
**Retrieve:** (`query` BM25 now zero-hits this doc-shaped graph — noise-label filtering; use `name_pattern` over the pagination/cache identifiers):
```bash
codebase-memory-mcp cli search_graph --project modelcontextprotocol \
  --name-pattern 'PaginatedResult|CacheableResult|nextCursor|ttlMs' --limit 15
```

## Verdict
Adopt opaque-cursor looping with missing-`nextCursor` termination, per-page TTL clocks, notification-driven invalidation, and the MRTR/`input_required` no-cache exclusions; adapt default TTLs and your cache-key parameter set to your product; omit treating cursors as structured data or using `cacheScope` as an authorization boundary — both are spec violations.
