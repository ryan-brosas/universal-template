---
name: listmonk-foundation
description: "Use when porting double-opt-in subscriber lifecycles, side-effecting campaign dispatch scans, waitgroup-drained send pipes, multi-provider bounce webhooks, or dry-run-guarded arbitrary-query bulk operations — listmonk newsletter/campaign dispatch kernel."
---
# listmonk: campaign dispatch & subscriber lifecycle foundation

## Use this for
Use when porting double-opt-in subscriber lifecycles, side-effecting campaign dispatch scans, waitgroup-drained send pipes, multi-provider bounce webhooks, or dry-run-guarded arbitrary-query bulk operations. Source code is ground truth; references carry decisive excerpts and graph retrieval. AGPL-3.0 — mine patterns, never verbatim code.

## Load the matching source dump
- `references/readonly-dryrun-query-composition.md` — two-phase dry-run/execute protocol for %query%-templated destructive statements.
- `references/subscriber-insert-optin-contract.md` — insert vs 409-exists vs optin-pending outcomes; SQL-side blocklist status mapping.
- `references/update-with-lists-permitted-scoping.md` — symmetric permitted-list guard around merge/replace subscription updates.
- `references/next-campaigns-side-effecting-scan.md` — CTE that flushes sent counters, claims scheduled campaigns, snapshots max_subscriber_id.
- `references/pipe-waitgroup-completion.md` — sentinel-WaitGroup drain protocol; cleanup-once final-status decision.
- `references/nonblocking-pipe-admission.md` — try-enqueue-or-release admission vs bounded-blocking transactional pushes.
- `references/sliding-window-and-rate-limits.md` — three limiters (worker tick, global sliding window, per-pipe gauge) and where each sleeps.
- `references/tracking-dummy-uuid-privacy.md` — dummy-UUID substitution lattice across render/ingest/aggregation.
- `references/bounce-threshold-action-ladder.md` — atomic count-in-SQL escalation to blocklist/unsubscribe/delete.
- `references/multi-provider-webhook-dispatch.md` — single-endpoint service routing with per-provider handshake headers.
- `references/sns-signature-verification-cache.md` — SNS cert-URL allowlist, SHA1WithRSA canonical serialization, race-safe cert cache.
- `references/campaign-status-ladder.md` — five-case manual transition ladder vs deliberate system-writer bypasses.
- `references/inline-image-cid-embed.md` — one-shot data-embed resolution with negative-result CID cache.
- `references/public-subscribe-resubscribe-form.md` — gate-before-write private-list defense and merge-on-conflict resubscribe.
- `references/importer-session-lifecycle.md` — singleton state machine over disposable batch-committing sessions.
- `references/email-domain-allow-blocklist.md` — single canonicalization choke point with first-label wildcard matching.
- `references/campaign-template-two-layer-compile.md` — AddParseTree grafting of body under base template with sanitized shared FuncMap.
- `references/tx-message-subscriber-modes.md` — default/fallback/external recipient resolution with reported partial success.
- `references/api-token-cache-auth.md` — deferred-failure middleware, hashed constant-time tokens, cookie-over-Basic precedence.
- `references/smtp-pool-from-address-routing.md` — bucketed-pointer round-robin with superset fallback pool.

## Capsule map
- **Arbitrary-query safety** — `readonly-dryrun-query-composition`: READ ONLY-tx dry run precedes every splice-executed delete/blocklist/export; boolean dry-run flag is bind #1 across the family.
- **Subscriber lifecycle** — `subscriber-insert-optin-contract`: created/409/optin-pending triad; blocklisted-at-insert unsubscribes atomically in SQL. `update-with-lists-permitted-scoping`: permitted-set wraps BOTH delete and upsert arms. `email-domain-allow-blocklist`: one SanitizeEmail choke point feeds subscribe/import/tx/bounce paths; allowlist wins over blocklist; `*.` wildcards also register bare domain.
- **Dispatch engine** — `next-campaigns-side-effecting-scan`: discovery+accounting in one CTE; static list-ID binds defeat planner regression (~15s→ms). `pipe-waitgroup-completion`: stop=mark/drain/cleanup-once; every queued message owes exactly one wg.Done(). `nonblocking-pipe-admission`: rejected pipes release their sentinel immediately; tx pushes block 3s instead. `sliding-window-and-rate-limits`: window state lives on Manager (global), sleep lands producer-side. `campaign-status-ladder`: five-case manual transition ladder validated against freshly-read DB state; system writers (cleanup, scan claim) deliberately bypass it.
- **Tracking & privacy** — `tracking-dummy-uuid-privacy`: privacy toggles transform VALUES consistently at render/ingest/aggregate; analytics registration fails open.
- **Bounce plane** — `bounce-threshold-action-ladder`: escalation atomic with recording, idempotent under retry, +1 computed in SQL. `multi-provider-webhook-dispatch`: raw-body preservation, parse-gate then record-fail-open, provider-specific handshake headers. `sns-signature-verification-cache`: cert URL allowlist BEFORE fetch; post-fetch double-check; never cache parse failures.
- **Content pipeline** — `inline-image-cid-embed`: per-campaign (not per-message) embed with cached misses. `campaign-template-two-layer-compile`: compile once per pipe; sprig env/exec/host deleted from FuncMap.
- **Public surface** — `public-subscribe-resubscribe-form`: private lists probed before any write; 409 → merge-resubscribe with allowResubscribe=true.
- **Bulk import** — `importer-session-lifecycle`: singleton status vs disposable session; skip-not-fatal rows; 10k tx batches; producer owns queue close.
- **Messaging APIs** — `tx-message-subscriber-modes`: external skips DB, fallback fabricates on miss, default reports misses as 400 after pushing hits. `smtp-pool-from-address-routing`: "" key = fallback AND superset.
- **Auth** — `api-token-cache-auth`: cookie presence disables header auth (upgrade compat); sha256 tokens compared constant-time; superadmin bypasses Perm.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Pass-2 candidates: Google_sync/Caldav-style transport twins are N/A here; prefer `internal/messenger/postback` SMS Messenger contract, OIDC login flow internals (`internal/auth/auth.go:151-286`), media upload/store abstraction (`cmd/media.go`, `internal/media`), dashboard stats rollups (`internal/core/dashboard.go`), or diff-first re-entry past `670c0171`.

## Provenance
listmonk (AGPL-3.0), `master@670c0171`; Codebase Memory project `ext-listmonk` (ready, root `/mnt/hdd/utopia/inspo/external/listmonk`, branch master@same sha == base_sha (zero drift), 28,857 nodes / 38,164 edges, gen 2026-08-23T11:45Z; parse_partial 16 files all HTML/SCSS/.sql templates — zero impact on cited Go paths; skipped 0). First squeeze pass; repo had NO learning row before this pass (row added same commit per row-gap rule).

## Full view (memory graph)
Revalidate `ext-listmonk` before porting: run `index_status --project ext-listmonk --verbose`, `check_index_coverage` (stdin JSON), `search_graph`, `trace_path`, and `get_code_snippet`. Root `/mnt/hdd/utopia/inspo/external/listmonk`, branch master@670c0171, 28,857 nodes / 38,164 edges. All 19 cited .go paths report `no_recorded_issue` on check_index_coverage at this pin; the three cited .sql query files are parse_partial (SQL text templates) — cite them by line number via source read, not graph spans. BM25 search_graph resolves Function/Method nodes line-exact (validateQueryTables :604-631, BounceWebhook :124-288, CompileTemplate :141-242 verified). Upstream ships ZERO *_test.go files — no direct test probes exist; every Probe is a deterministic byte-exact source pin executed pre-authoring (battery: `.pi/work/foundations-deep-farm/listmonk-p1-probes.sh`, 40 checks green after 2 re-derived).

## Boundaries
Adopt pure contracts: the dry-run query-composition protocol, optin/409 subscriber contract, permitted-list scoping, checkpointed dispatch scan, sentinel-waitgroup drain, try-enqueue admission, count-in-SQL bounce escalation, cert-allowlisted webhook verification, dummy-UUID privacy substitution, and single-chokpoint email canonicalization. Adapt Go channel/atomic idioms to your runtime's equivalents, sqlx/pq adapters to your driver, echo middleware ordering to your router, and i18n keys to your strings. Omit product surfaces: Vue admin frontend (`frontend/`), archive rendering views, media/S3 store backends beyond the interface, install wizard, docker/systemd packaging, and bounces-by-mailbox (POP) polling internals.
