<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# umami: privacy-first web analytics platform

## Use this for
Use when porting privacy-first analytics/telemetry machinery: cookieless derived session identity, rolling cache-token handshakes for anonymous ingest, dual-backend SQL dispatch (Postgres + ClickHouse), dynamic filter compilation with typed bind placeholders, Kafka wire-size batching, soft-delete read caches, 2FA with partial-auth tokens and replay ledgers, rrweb session-replay chunking/reassembly, heatmap capture with scroll bucketing, hand-rolled Core Web Vitals, and share-token capability grants. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./cache-token-handshake.md` — how an anonymous tracker gets a server-side session without a login.
- `./derived-identity-uuid.md` — cookieless stable session ids via salted uuidv5 with rotation windows.
- `./pwd-fingerprint-auth.md` — password-change token invalidation carried in the token itself.
- `./partial-auth-2fa.md` — two-step login scoped by a typed 5-minute intermediate credential.
- `./totp-crypto-replay.md` — GCM-encrypted TOTP secrets plus a 90-second OTP replay ledger.
- `./2fa-serializable-lockout.md` — serializable increment-and-lock attempt counters that close the race.
- `./backup-codes-consume.md` — hashed recovery codes burned by conditional UPDATE.
- `./runquery-dispatch.md` — constant-keyed per-query backend selection with result-shape parity contract.
- `./clickhouse-filter-compiler.md` — JSON filter bag → whitelisted, placeholder-bound CH SQL incl. cohort joins.
- `./property-filter-trio.md` — EAV property filters via group-having anti-joins in both dialects.
- `./paged-capped-envelope.md` — capped-count pagination with an honest isCapped flag.
- `./kafka-wire-size-batching.md` — greedy byte-size batch flushes; poison records dropped fail-open.
- `./redis-soft-delete-cache.md` — sentinel-based negative caching + single-flight reconnect.
- `./prisma-raw-rewrite-replica.md` — `{{name::cast}}` → `$n` rewriting with explicit read/write client routing.
- `./client-ip-ladder.md` — ordered CDN header resolution with v4-mapped/port normalization.
- `./geo-header-precedence.md` — provider-table geo headers vs MaxMind fallback, all-or-nothing adoption.
- `./tracker-bootstrap-gates.md` — data-attribute config, DNT/local opt-out gates, idempotent global API.
- `./spa-hooks-click-capture.md` — pushState wrapping + capture-phase delegated click events that defer navigation until send.
- `./web-vitals-session-windows.md` — manual TTFB/FCP/LCP/CLS/INP with session-window CLS and p98 INP.
- `./rrweb-fragment-chunking.md` — binary-search payload fragmentation with id-keyed reassembly.
- `./replay-playability-normalization.md` — structural playability checks + monotone timestamp repair.
- `./recorder-bootstrap-sampling.md` — remote config fetch, independent sampling, session-readiness polling.
- `./heatmap-capture-bucketing.md` — event-time page dimensions, max-scroll tracking, fixed-depth buckets.
- `./send-admission-pipeline.md` — the exact validation ladder from untrusted POST to stored event.
- `./session-data-flattening.md` — nested identify() JSON → typed KV rows with upsert idempotency.
- `./date-range-unit-ladder.md` — span-driven unit selection and tz-aware range snapping.
- `./suffixed-filter-wire-format.md` — repeated GET filters (`browser1`) + operator-prefixed values round-trip.
- `./share-token-capability.md` — type-tagged capability tokens with mint-time scope expansion.
- `./realtime-composition.md` — one fold building activity feed, dedup markers, series and totals.
- `./batch-request-fanout.md` — in-process handler reuse with Request reconstruction and cache chaining.
- `./collect-cors-fairing.md` — exact-header CORS allowlist wrapped over every exit path.
- `./gcm-envelope-helpers.md` — positional AES-256-GCM envelopes and null-returning verify wrappers.

## Capsule map
- **Identity & sessions** — `cache-token-handshake`: rolling type-tagged cache JWT skips DB on repeat hits; `derived-identity-uuid`: salted uuidv5 sessions with month/hour rotation and 30-min visit expiry.
- **Auth & 2FA** — `pwd-fingerprint-auth`: hash-of-hash fingerprints kill tokens on password change; `partial-auth-2fa`: typed 5m intermediate credentials; `totp-crypto-replay`: encrypted secrets + 90s ledger; `2fa-serializable-lockout`: serializable increment-and-lock; `backup-codes-consume`: conditional-UPDATE single-use codes; `gcm-envelope-helpers`: positional GCM framing + catch-null verify.
- **Query engine** — `runquery-dispatch`: string-keyed dual-backend routing; `clickhouse-filter-compiler`: whitelist columns, typed placeholders, always-AND constraints; `property-filter-trio`: group-having anti-joins, tuple session joins; `paged-capped-envelope`: capped counts + isCapped; `date-range-unit-ladder`: span→unit snapping; `suffixed-filter-wire-format`: suffix identity + operator prefixes.
- **Ingest pipeline** — `send-admission-pipeline`: schema→cache→bot→blocklist→derive→branch ordering; `session-data-flattening`: typed dot-key KV upserts; `batch-request-fanout`: sequential handler reuse preserving cache chaining; `collect-cors-fairing`: exact allowlist, all exits wrapped.
- **Streaming infra** — `kafka-wire-size-batching`: greedy size flush, drop-and-log oversize, fail-open errors; `redis-soft-delete-cache`: DELETED sentinel negative cache, single-flight connect; `prisma-raw-rewrite-replica`: named→positional rewrite, $primary/$replica routing.
- **Tracker (browser)** — `tracker-bootstrap-gates`: attribute config + layered disable gates; `spa-hooks-click-capture`: history hooks + capture-phase delegation with send-before-navigate; `web-vitals-session-windows`: hand-rolled CWV with worst-window CLS and floored p98 INP.
- **Session replay** — `rrweb-fragment-chunking`: binary-search fragments, monotone chunk clock, tolerant reassembly; `replay-playability-normalization`: structural FullSnapshot check + timestamp repair; `recorder-bootstrap-sampling`: remote config, independent coin flips, cache-token wait.
- **Heatmap** — `heatmap-capture-bucketing`: event-time dimensions, max-scroll debounce, 10-point buckets, server clamps.
- **Access & views** — `client-ip-ladder`: priority header walk with normalization; `geo-header-precedence`: provider table vs MaxMind, skip-headers rule; `share-token-capability`: type-gated tokens + board scope expansion at mint time; `realtime-composition`: double-reverse fold with session markers.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Pass-1 thesis: the reusable core is not "an analytics tool" but the UNTRUSTED-INGEST ARCHITECTURE — derive identity instead of storing it, gate every write through an ordered admission ladder, compile user filters into whitelisted parameterized SQL, stream through size-bounded queues that fail open, and pair each client collector with a strict server-side re-validation twin.

## Provenance
umami v3.3.1 (MIT), `master@ca661c7057984aa98ed4f7083d84dae2f65bfcb0`; Codebase Memory project `ext-umami` (ready FULL 81,954n/109,900e gen 2026-08-23T12:02Z generation_matches=true; head==base==pin == origin/master at pass 1, zero drift; parse_partial ×33 = ClickHouse/Prisma migration SQL + 3 UI test files, none cited; not_indexed = images/assets by design).

## Full view (memory graph)
Revalidate `ext-umami` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Coverage stdin-JSON on all 46 cited paths returned no_recorded_issue + metadata_match; BM25 resolves every seam symbol line-exact (jwt/crypto/auth/runQuery/mapFilter/property-filter/replay/recorder families); wrong-project probes (rrweb@ext-vaultwarden, positionCaseInsensitive@ext-bruno) return total:0. Upstream ships a vitest suite concentrated on lib/ pure functions (auth fingerprint ladder, ip normalization, params round-trip, recorder-config validation, replay reassembly, date grammar); route handlers and query bodies are source-pinned only — runner BLOCKED in this environment (no node_modules in inspo clone), so all Probes are deterministic pins per protocol.

## Boundaries
Adopt the pure contracts: derived identity, rolling cache tokens, typed capability gates, ordered admission ladders, whitelist+placeholder SQL compilation, size-bounded fail-open streaming, sentinel caches, fragment reassembly protocols, serializable security counters. Adapt: Next.js route handlers to your framework, Prisma/pg to your ORM, kafkajs/redis clients to your queue/cache tier, otplib+bcryptjs choices, rrweb version specifics, data-attribute names. Omit: the React dashboard app (src/app/(main), components/, queries client hooks), i18n/locales, boards UI composition beyond the share-scope seam, cloud-mode billing surfaces (subscription/teams gating), Docker/proxy deployment files, seed scripts, prisma/clickhouse migration corpora.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`2fa-serializable-lockout.md`](./2fa-serializable-lockout.md)
- [`backup-codes-consume.md`](./backup-codes-consume.md)
- [`batch-request-fanout.md`](./batch-request-fanout.md)
- [`cache-token-handshake.md`](./cache-token-handshake.md)
- [`clickhouse-filter-compiler.md`](./clickhouse-filter-compiler.md)
- [`client-ip-ladder.md`](./client-ip-ladder.md)
- [`collect-cors-fairing.md`](./collect-cors-fairing.md)
- [`date-range-unit-ladder.md`](./date-range-unit-ladder.md)
- [`derived-identity-uuid.md`](./derived-identity-uuid.md)
- [`gcm-envelope-helpers.md`](./gcm-envelope-helpers.md)
- [`geo-header-precedence.md`](./geo-header-precedence.md)
- [`heatmap-capture-bucketing.md`](./heatmap-capture-bucketing.md)
- [`kafka-wire-size-batching.md`](./kafka-wire-size-batching.md)
- [`paged-capped-envelope.md`](./paged-capped-envelope.md)
- [`partial-auth-2fa.md`](./partial-auth-2fa.md)
- [`prisma-raw-rewrite-replica.md`](./prisma-raw-rewrite-replica.md)
- [`property-filter-trio.md`](./property-filter-trio.md)
- [`pwd-fingerprint-auth.md`](./pwd-fingerprint-auth.md)
- [`realtime-composition.md`](./realtime-composition.md)
- [`recorder-bootstrap-sampling.md`](./recorder-bootstrap-sampling.md)
- [`redis-soft-delete-cache.md`](./redis-soft-delete-cache.md)
- [`replay-playability-normalization.md`](./replay-playability-normalization.md)
- [`rrweb-fragment-chunking.md`](./rrweb-fragment-chunking.md)
- [`runquery-dispatch.md`](./runquery-dispatch.md)
- [`send-admission-pipeline.md`](./send-admission-pipeline.md)
- [`session-data-flattening.md`](./session-data-flattening.md)
- [`share-token-capability.md`](./share-token-capability.md)
- [`spa-hooks-click-capture.md`](./spa-hooks-click-capture.md)
- [`suffixed-filter-wire-format.md`](./suffixed-filter-wire-format.md)
- [`totp-crypto-replay.md`](./totp-crypto-replay.md)
- [`tracker-bootstrap-gates.md`](./tracker-bootstrap-gates.md)
- [`web-vitals-session-windows.md`](./web-vitals-session-windows.md)
