---
name: supabase-foundation
description: Use when porting Supabase studio dashboard machinery — typed OpenAPI fetch-client kernel with middleware error enrichment, duck-typed error classification ladder, HTTP/3 empty-body normalization, pg-meta fail-fast connection guard, SQL execution guard ladder with role-impersonation line rewinding, contextual cache invalidation, the react-query data-module recipe with retryAfter-aware retry gating, the pg-meta branded-SQL taint kernel with ident/literal/keyword escaping ladders, the structured filter compiler, and the guarded query-builder pipeline.
---

# Supabase: studio API data-fetching kernel foundation

## Use this for
Use when porting a dashboard-style typed API client layer: openapi-fetch client assembly with auth/request-id headers, error-body enrichment middleware, message-regex error classification into typed ResponseError subclasses, transport-level empty-body fixes, fail-fast DB-connection guards, guarded SQL-execution mutations over pg-meta, broad contextual query-cache invalidation, or per-module react-query hooks backed by a global retry gate that reads enriched error fields. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/openapi-client-kernel.md` — how do I assemble one typed fetch client whose transport translates network failures and mints per-request identity headers?
- `references/empty-body-http3-normalizer.md` — why do 201-with-empty-body responses succeed on HTTP/2 but throw "Unexpected end of JSON input" on HTTP/3?
- `references/pg-meta-guard-error-enrichment-middleware.md` — where do errors get requestId/retryAfter/code/requestPathname injected, and when does the client refuse to hop to the database at all?
- `references/handle-error-classification-ladder.md` — how does a raw API error body become a typed, field-preserving ResponseError without leaking internals to UI?
- `references/dual-fetch-plane-contract.md` — when must I use the legacy fetchGet/fetchPost trio instead of the typed client, and what compat hack keeps old callers alive?
- `references/execute-sql-guard-ladder.md` — what stands between user SQL and Postgres: size caps, EXPLAIN cost preflight, impersonation line-number rewinding, and the no-results sentinel?
- `references/sql-mutation-contextual-invalidation.md` — how does one DDL mutation invalidate exactly the right slice of the query cache while emitting telemetry?
- `references/react-query-data-module-recipe.md` — what is the exact shape of a `*-query.ts` data module, and how does the global retry gate consume retryAfter/requestPathname?
- `references/sql-taint-brand-kernel.md` — how do I make untrusted SQL unrepresentable as executable at the type level?
- `references/pg-format-ident-feexec-port.md` — when does an identifier stay bare and how are the rest quoted?
- `references/pg-format-literal-escaping-ladder.md` — how does any JS value become an injection-proof SQL literal?
- `references/pg-format-keyword-allowlist.md` — how can a UI-supplied SQL keyword be interpolated without becoming an injection channel?
- `references/pg-format-specifier-engine.md` — what are the exact `%s/%I/%L` + `%n$` positional semantics, including argument reuse?
- `references/query-filter-compiler.md` — how do structured filters become a WHERE clause without string concatenation?
- `references/query-chain-toSql-pipeline.md` — what is the builder chain from `Query.from(...)` to SQL, and which guards stop unbounded DML?
- `references/helpers-list-guard-plane.md` — how do IN-clauses, row aggregation, and identifier lookups avoid bare `IN ()` and degenerate SQL?

## Capsule map

### Typed client kernel (`data/fetchers.ts`)
- **Transport + identity** — `openapi-client-kernel`: `fetchHandler` converts only `TypeError: Failed to fetch` into an actionable Error; `constructHeaders` mints uuidv4 `X-Request-Id` per request and sets Bearer auth only when the caller has not already set Authorization (caller override wins).
- **Empty-body normalizer** — `empty-body-http3-normalizer`: clone-read-rebuild injects `Content-Length: 0` on empty non-204 bodies so openapi-fetch's JSON parse short-circuits regardless of HTTP version.
- **Middleware pair** — `pg-meta-guard-error-enrichment-middleware`: `pgMetaGuard` throws ResponseError before the server hop when `x-connection-encrypted` is missing on `/platform/pg-meta/` calls; `onResponse` rewrites error JSON bodies with code/requestId/retryAfter (`Retry-After` ?? `X-RateLimit-Reset`)/requestPathname.
- **Error classification** — `handle-error-classification-ladder`: strict duck-typed field extraction (`msg` beats `message`, typeof-checked numerics), regex→class map built from a Map so duplicate registration is impossible by construction, vague-message fallback for UI safety; direct test pins msg-priority, case-insensitive timeout matching, and field preservation.

### Legacy + SQL planes
- **Dual fetch plane** — `dual-fetch-plane-contract`: dashboard-only endpoints use fetchGet/fetchPost/fetchHeadWithTimeout with octet-stream passthrough and HEAD header projection; `handleFetchError` sets `error.error = error` as a ts-expect-error'd compatibility shim for legacy `if (response.error)` checks.
- **SQL guard ladder** — `execute-sql-guard-ladder`: projectRef gate → 0.98 MB Blob-size cap → optional EXPLAIN preflight rejecting cost ≥ 200_000 with `{cost, sql}` metadata (preflight failure never blocks UI) → role-impersonation `LINE n:` rewind by the pinned 11-line wrapper height → `ROLE_IMPERSONATION_NO_RESULTS` marker-row collapse to `[]`.
- **Contextual invalidation** — `sql-mutation-contextual-invalidation`: create/alter/drop detection sweeps all `['projects', ref]` keys minus a five-entry ignore list; sqlEventParser telemetry is fail-soft; onError defaults to toast.

### Consumer pattern
- **Data module recipe** — `react-query-data-module-recipe`: private fetch fn (throw-if-required → typed call → `if (error) handleError(error)`), exported `Awaited<ReturnType>` data type, keys factory rooted at `['projects', projectRef, ...]`, signal threading, enabled-gating on defined projectRef, per-hook retry overrides; global QueryClient gate skips 4xx retries except 429, honors `retryAfter * 1000` backoff, suppresses window-focus/reconnect refetch after statement timeouts.

### pg-meta SQL-safety kernel (`packages/pg-meta`)
- **Taint-brand kernel** — `sql-taint-brand-kernel`: `SafeSqlFragment`/`UntrustedSqlFragment`/`DisplayableSqlFragment` phantom brands; the `safeSql` tag accepts ONLY branded interpolations (plain string/number/object is a compile error); escape hatches are closed — `rawSql` for user-authored editor SQL, `acceptUntrustedSql` promotion allowed only inside a deliberate user-action event handler.
- **ident() ladder** — `pg-format-ident-feexec-port`: libpq fe-exec.c port; bare fast path requires `/^[_a-z][\d$_a-z]*$/` AND non-reserved membership; else double-quote with `"` doubling; booleans → `"t"/"f"`, Date → quoted ISO, one-level array flatten, null/object/nested-array throw.
- **literal() ladder** — `pg-format-literal-escaping-ladder`: NULL → specials (bigint/±Infinity/NaN) before generic number → `'t'/'f'` → ISO date → array recursion → object as `'json'::jsonb`; string body doubles BOTH `'` and `\`, any backslash flips prefix to explicit-escape `E''`.
- **keyword() gate** — `pg-format-keyword-allowlist`: single-word regex OR case-insensitive closed Set (`'INSTEAD OF'`, `'BY DEFAULT'`) with original casing preserved; everything else throws — "DROP TABLE" cannot slip through.
- **Specifier engine** — `pg-format-specifier-engine`: `%I/%L/%s` from mutable config regex; `%n$` positions advance the sequential cursor past n, enabling argument reuse (`%1$s ... null::%1$s` in insert/update builders); arg-0 and out-of-range throw. `%s` does NOT escape.
- **Filter compiler** — `query-filter-compiler`: operator dispatch with tuple arms (arity-checked, operator-restricted), whitelisted `is null/false/true/not null`, `::text` cast for LIKE-family ops, and an ARRAY[...] literal parser that validates the cast suffix or falls back to plain `literal()` re-escaping.
- **Builder pipeline** — `query-chain-toSql-pipeline`: Query.from(schema-default 'public') → stateless QueryAction verbs → QueryFilter accumulators (structuredClone reuse) → fresh QueryModifier projection per terminal toSql; delete/update THROW on empty filters at the SQL-builder layer; range(from,to) = `{offset: from, limit: to-from+1}` inclusive.
- **List-guard helpers** — `helpers-list-guard-plane`: filterByList include-wins tri-state never emits bare `IN ()`; coalesceRowsToArray COALESCE-empty-array wrapper with optional deterministic inner ORDER BY; getIdentifierWhereClause id | name+schema | fail-loud trichotomy repeated across pg-meta entity modules.

### Studio consumer bridge
The studio grid plane imports this kernel directly: `apps/studio/data/table-rows/table-rows-query.ts:1-3` pulls `ident/joinSqlFragments/safeSql/ROLE_IMPERSONATION_NO_RESULTS`, `Query`, and `getTableRowsSql` from `@supabase/pg-meta` and feeds composed SQL through pass-1's execute-sql guard ladder — port the two planes together.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Revalidate the `supabase` graph project before porting and diff against pin `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`.

## Provenance
Supabase (Apache-2.0), `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory project `supabase` (FULL mode, generation 2026-08-25T19:56:24Z, 94,325 nodes / 332,119 edges). Coverage caveats at mining time: 192 parse-partial files (CSS/SQL/docs/test ranges — none among cited TS paths except `packages/pg-meta/src/query/index.ts:6`, a 6-line barrel read directly); 2 skipped vendored monaco bundles (never citable); image/env exclusions by design. Pass 1 mined the studio data-fetching kernel; pass 2 deepened into the pg-meta SQL-safety kernel + query builder at the identical pin.

## Full view (memory graph)
Revalidate `supabase` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: header identity rules, error-field enrichment grammar, classification ladder, guard ladders, invalidation sweep semantics, retry-gate arithmetic. Adapt host-specific integration: openapi-fetch/openapi-typescript wiring, @tanstack/react-query defaults, Sentry capture, sonner toasts, pg-meta endpoint paths, valtio/zustand state feeds. Omit Supabase-product behavior: platform env topology (`/platform` URL rewriting), feature-flag gating, billing/usage surfaces, and the studio's own component/UI layers.
