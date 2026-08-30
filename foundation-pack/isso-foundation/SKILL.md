---
name: isso-foundation
description: "Use when porting Isso's self-hosted comment-server internals: SQLite comment/thread storage, moderation modes, guard rate limits, signed edit/moderation tokens, notification fanout, sanitizer pipeline, or the multi-mixin WSGI deployment core."
disable-model-invocation: true
---

# Isso: lightweight comment server — storage, moderation, and embedding kernel

## Use this for
Building or porting any third-party commenting/embeddable-discussion backend (Disqus-style): thread-on-demand creation with title scraping, parent-validated replies flattened to one level, pending/published/tombstone moderation modes, per-IP guard limits, bloom-filter vote dedupe, salted author hashing, signed per-comment edit cookies and emailed moderation links, SMTP reply notifications with List-Unsubscribe, Disqus/WordPress/Generic importers, bleach-based sanitization, and a threaded/process/uWSGI deployment spine. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump

Storage & queries
- `references/parent-reanchor.md` — how reply parents are validated same-thread and re-anchored to valid ancestors.
- `references/add-maxid-readback.md` — atomic INSERT..SELECT from threads plus MAX(c.id) row readback.
- `references/soft-delete-cascade.md` — mode-4 tombstones vs hard delete and the fixpoint stale sweep.
- `references/orphan-trigger.md` — DB trigger deriving thread lifetime from comment presence.
- `references/sqlite-execute-per-call.md` — connection-per-execute wrapper and where transactions live instead.
- `references/migration-ladder.md` — PRAGMA user_version rungs 0–5, transactional bumps, idempotence probes.
- `references/nesting-flatten-migration.md` — collapsing arbitrary depth onto top-level roots in one migration.
- `references/karma-mode-mask.md` — bitwise `(mode | comments.mode) = ?` visibility masks and the two spellings' trap.
- `references/threaded-orderby.md` — whitelist + CASE parents-first ordering that keeps replies under roots.
- `references/approved-author-fastpath.md` — 6-month mode-1 EXISTS auto-approval inside the write lock.
- `references/unsubscribe-scope.md` — email-scoped id-or-parent notification muting.
- `references/vote-blob-cap.md` — 256-byte bloom voter blobs, 142-vote cap, count+blob co-write invariant.
- `references/admin-listing-plane.md` — admin paging/sorting/URL-search and signed link tokens in tables.

HTTP surface & security
- `references/edit-cookie-shape.md` — shape-check-before-index on shared-signer payloads + sha1(text) revision binding.
- `references/csrf-json-gate.md` — Content-Type application/json as the form-forgery boundary.
- `references/moderation-token-twin.md` — max_age=2**32 emailed action tokens vs 15-min edit cookies.
- `references/cookie-samesite.md` — https⇒Secure+SameSite=None vs Lax ladder and dual Set-Cookie headers.
- `references/remote-addr-trusted-proxy.md` — right-to-left XFF walk over trusted proxies + anonymize-at-ingestion.
- `references/hash-cache-invalidation.md` — namespaced author-hash memoization and eviction on delete.
- `references/input-verification-whitelist.md` — ACCEPT input allowlist vs FIELDS output projection and per-field escaping.
- `references/latest-deque.md` — feature-flagged last-N via bounded deque over ascending scan.

- `references/guard-limits.md` — ratelimit/direct-reply/reply-to-self-window/require-* first-failure ladder.
- `references/moderation-confirm-modal.md` — GET confirm modal re-issued as POST with JSON-encoded redirect.
- `references/hidden-replies-ledger.md` — grouped counts + derived hidden arithmetic and the nested offset reset.

Boot & serve spine
- `references/cli-bootstrap-ladder.md` — ISSO_SETTINGS-over-flag precedence and the http/unix listen→runtime ladder.
- `references/app-assembly-order.md` — db-before-signer ordering, implicit-SMTP rule, self-registering views, fatal-vs-warn boot checks.
- `references/dispatch-error-funnel.md` — thread-local setup, three-arm error funnel, accept-negotiated JSON errors.
- `references/socket-server-unix-ladder.md` — AF_UNIX class flags and the pre-dispatch client-address fake.
- `references/dump-comments-export-plane.md` — read-only single-SELECT exporter with in-memory reply reassembly.

Rendering & content pipeline
- `references/markup-render-selection.md` — fail-closed mistune/misaka selection, forced escape, read-time rendering, p-wrapper.
- `references/sanitizer-link-policy.md` — bleach allowlists, rel nofollow/noopener, invented-link suppression, language-* classes.
- `references/thread-title-scraping.md` — ancestors-then-up h1 walk from #isso-thread with data-title/data-isso-id overrides.

Notifications & extensions
- `references/signal-extension-bus.md` — iterable-subscriber Signal and the full comments.* event set.
- `references/smtp-reply-fanout.md` — opt-in sibling+parent audience with five-condition exclusion guard.
- `references/list-unsubscribe-header.md` — self-describing ("unsubscribe", email) tokens in mail headers.
- `references/smtp-retry-senders.md` — uWSGI spooler vs start_new_thread range(5) connect-retry dispatch.
- `references/moderation-purge-loop.md` — purge-after sweeper sharing the writer lock across mixins.
- `references/session-key-signer.md` — DB-persisted random signing key and every payload shape it carries.

Deployment & import
- `references/runtime-cache-mixins.md` — NullCache/SimpleCache/uWSGICache behind one namespace-dropping facade.
- `references/origin-negotiation.md` — closed allowlist Origin/Referer reflection for credentials-true CORS.
- `references/cors-suburi-stack.md` — make_app wrapper order: local→SharedData→CORS→SubURI→ProxyFix(x_prefix).
- `references/config-parser-dialect.md` — timedelta ints, getlist/getiter, expandvars, load-time typo linting.
- `references/curl-outbound-client.md` — never-raising httplib wrapper with path-only 301 retry.
- `references/title-fetch-on-create.md` — locked check-and-create thread with origin-validated page scrape fallback.
- `references/disqus-import-remap.md` — chronological dsq:id→integer remap with post-GC orphan report.
- `references/wordpress-import-fixpoint.md` — deferred-worklist insertion with for-else termination bail.
- `references/import-dispatch-autodetect.md` — one-buffer format sniffing, guard-off bulk imports, non-empty prompt.
- `references/feed-conditional-etag.md` — head-comment etag/last-modified conditional Atom feeds.
- `references/multisite-dispatch.md` — name-keyed app mounting and the X-Script-Name pop trap.

## Capsule map
- **Threaded storage** — `parent-reanchor`: same-thread EXISTS check + recurse-or-null re-anchor; `add-maxid-readback`: INSERT..SELECT tid-from-uri + MAX(c.id) zip(fields); `soft-delete-cascade`: tombstone referenced rows, while-rowcount stale sweep; `orphan-trigger`: AFTER DELETE trigger GCs empty threads; `sqlite-execute-per-call`: stateless connections, migrations own their transactions.
- **Schema evolution** — `migration-ladder`: version-bump-inside-transaction rungs + table_info idempotence; `nesting-flatten-migration`: collect-per-root then rewrite parents in one COMMIT.
- **Visibility & ordering** — `karma-mode-mask`: subset bitmask predicates (two spellings, don't normalize); `threaded-orderby`: whitelisted dynamic ORDER BY under a NULL-emitting parents-first CASE.
- **Moderation & trust** — `approved-author-fastpath`: locked 6-month EXISTS flip 2→1; `unsubscribe-scope`: email AND (id OR parent) muting; `admin-listing-plane`: signed link tokens + fragment-aware URL search; `moderation-purge-loop`: delta-period mode-2 sweeper under writer lock.
- **Anti-abuse** — `vote-blob-cap`: bloom blob + counts must move together, cap at FP knee 142; `guard-limits`: ratelimit/direct-reply/reply-to-self-window/require-* first-failure ladder; `moderation-confirm-modal`: GET renders confirm, POST executes, link JSON-encoded; `hidden-replies-ledger`: one grouped count, hidden = count−shown−offset, nested offset reset; `input-verification-whitelist`: ACCEPT-in/FIELDS-out governance with reason-returning verify.
- **Identity & crypto** — `session-key-signer`: DB-minted random key, one serializer many shapes; `edit-cookie-shape`: isinstance/len shape guard + sha1(text) checksum; `moderation-token-twin`: 2**32 max-age mail links; `remote-addr-trusted-proxy`: reversed-trust-walk + /24,/48 anonymize; `hash-cache-invalidation`: "hash" namespace eviction on delete.
- **Embedding surface** — `cookie-samesite`: scheme-derived Secure/SameSite pairing, X-Set-Cookie twin; `csrf-json-gate`: JSON Content-Type boundary; `origin-negotiation`: reflect-allowlisted-or-default; `cors-suburi-stack`: wrapper order + OPTIONS short-circuit; `latest-deque`: flag-gated bounded-deque latest-N.
- **Boot & serve spine** — `cli-bootstrap-ladder`: env-beats-flag config + protocol dispatch; `app-assembly-order`: store→key→mixin→views wiring with fatal/warn split; `dispatch-error-funnel`: one funnel for misses/crashes, MIME-gated JSON; `socket-server-unix-ladder`: AF_UNIX flags + synthetic peer address; `dump-comments-export-plane`: no-app-stack threaded dump.
- **Content pipeline** — `markup-render-selection`: fatal unknown renderer, escape forced, <p> wrap rule; `sanitizer-link-policy`: clean→linkify with new-link suppression; `thread-title-scraping`: upward nearest-h1 DOM walk.
- **Events & mail** — `signal-extension-bus`: iterable subscribers, synchronous inline fanout; `smtp-reply-fanout`: parent+sibling opt-ins, five exclusions; `list-unsubscribe-header`: tagged signed tuple URLs; `smtp-retry-senders`: spool vs thread retry transports.
- **Ingest** — `disqus-import-remap`: time-sorted remap + orphan report; `wordpress-import-fixpoint`: worklist with for-else bail + newline hard-breaks; `import-dispatch-autodetect`: peek-sniff, guard-off, dry-run temp DB.
- **Ops spine** — `runtime-cache-mixins`: backend swap per mixin, prune-on-set; `config-parser-dialect`: durations-as-ints + typo lint + expandvars; `curl-outbound-client`: None-on-failure client; `title-fetch-on-create`: locked create-or-scrape; `feed-conditional-etag`: head-item validators; `multisite-dispatch`: name mounts + header pop.

## Extending the foundation
Add one source-confirmed capsule: loader line, map entry, decisive source, invariant, direct-test probe, and `search_graph` retrieval. Next-pass candidates live in the work record `inspo/.skill-mining-work/isso/state.md` (notifications format() interiors, contrib/import_blogger.py ingest sibling).

## Provenance
isso (MIT), `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory project **`isso`** (root `/mnt/hdd/utopia/inspo/isso`, branch master, FULL, 1,756n/5,364e, generation 2026-08-26T01:41Z; parse_partial confined to SCSS/nginx/sample cfg/docs/templates — none cited). History: pass 1 mined 45 capsules against the now-retired twin project `ext-isso` @ `/mnt/hdd/utopia/inspo/external/isso` at the IDENTICAL HEAD (suite executed GREEN 118/118 via uv venv on 2026-08-24); pass 2 re-established the graph as short-name project `isso` and verified pin parity — older capsules' `project: "ext-isso"` Retrieve calls should substitute `isso`.

## Full view (memory graph)
Revalidate `isso` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Pass-2 coverage stdin sweep ×5 newly cited paths (`isso/__init__.py`, `isso/wsgi.py`, `isso/core.py`, `contrib/dump_comments.py`, `isso/tests/test_wsgi.py`) all `no_recorded_issue` + `metadata_match`; pass 1 recorded a 23-path clean sweep at the same HEAD.

## Boundaries
Adopt the pure contracts: mode-masked visibility, tombstone GC, token-shape discipline, origin allowlisting, anonymize-at-ingestion, event-bus lifecycle. Adapt SQLite spellings, cookie/header names, thresholds, and template plumbing to your host. Omit isso-specific product surfaces: the JS embed client (`isso/js`), demo page, admin HTML templates, and packaging scripts.
