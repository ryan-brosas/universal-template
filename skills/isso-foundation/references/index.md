<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Isso: lightweight comment server — storage, moderation, and embedding kernel

## Use this for
Building or porting any third-party commenting/embeddable-discussion backend (Disqus-style): thread-on-demand creation with title scraping, parent-validated replies flattened to one level, pending/published/tombstone moderation modes, per-IP guard limits, bloom-filter vote dedupe, salted author hashing, signed per-comment edit cookies and emailed moderation links, SMTP reply notifications with List-Unsubscribe, Disqus/WordPress/Generic importers, bleach-based sanitization, and a threaded/process/uWSGI deployment spine. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump

Storage & queries
- `./parent-reanchor.md` — how reply parents are validated same-thread and re-anchored to valid ancestors.
- `./add-maxid-readback.md` — atomic INSERT..SELECT from threads plus MAX(c.id) row readback.
- `./soft-delete-cascade.md` — mode-4 tombstones vs hard delete and the fixpoint stale sweep.
- `./orphan-trigger.md` — DB trigger deriving thread lifetime from comment presence.
- `./sqlite-execute-per-call.md` — connection-per-execute wrapper and where transactions live instead.
- `./migration-ladder.md` — PRAGMA user_version rungs 0–5, transactional bumps, idempotence probes.
- `./nesting-flatten-migration.md` — collapsing arbitrary depth onto top-level roots in one migration.
- `./karma-mode-mask.md` — bitwise `(mode | comments.mode) = ?` visibility masks and the two spellings' trap.
- `./threaded-orderby.md` — whitelist + CASE parents-first ordering that keeps replies under roots.
- `./approved-author-fastpath.md` — 6-month mode-1 EXISTS auto-approval inside the write lock.
- `./unsubscribe-scope.md` — email-scoped id-or-parent notification muting.
- `./vote-blob-cap.md` — 256-byte bloom voter blobs, 142-vote cap, count+blob co-write invariant.
- `./admin-listing-plane.md` — admin paging/sorting/URL-search and signed link tokens in tables.

HTTP surface & security
- `./edit-cookie-shape.md` — shape-check-before-index on shared-signer payloads + sha1(text) revision binding.
- `./csrf-json-gate.md` — Content-Type application/json as the form-forgery boundary.
- `./moderation-token-twin.md` — max_age=2**32 emailed action tokens vs 15-min edit cookies.
- `./cookie-samesite.md` — https⇒Secure+SameSite=None vs Lax ladder and dual Set-Cookie headers.
- `./remote-addr-trusted-proxy.md` — right-to-left XFF walk over trusted proxies + anonymize-at-ingestion.
- `./hash-cache-invalidation.md` — namespaced author-hash memoization and eviction on delete.
- `./input-verification-whitelist.md` — ACCEPT input allowlist vs FIELDS output projection and per-field escaping.
- `./latest-deque.md` — feature-flagged last-N via bounded deque over ascending scan.

- `./guard-limits.md` — ratelimit/direct-reply/reply-to-self-window/require-* first-failure ladder.
- `./moderation-confirm-modal.md` — GET confirm modal re-issued as POST with JSON-encoded redirect.
- `./hidden-replies-ledger.md` — grouped counts + derived hidden arithmetic and the nested offset reset.

Boot & serve spine
- `./cli-bootstrap-ladder.md` — ISSO_SETTINGS-over-flag precedence and the http/unix listen→runtime ladder.
- `./app-assembly-order.md` — db-before-signer ordering, implicit-SMTP rule, self-registering views, fatal-vs-warn boot checks.
- `./dispatch-error-funnel.md` — thread-local setup, three-arm error funnel, accept-negotiated JSON errors.
- `./socket-server-unix-ladder.md` — AF_UNIX class flags and the pre-dispatch client-address fake.
- `./dump-comments-export-plane.md` — read-only single-SELECT exporter with in-memory reply reassembly.

Rendering & content pipeline
- `./markup-render-selection.md` — fail-closed mistune/misaka selection, forced escape, read-time rendering, p-wrapper.
- `./sanitizer-link-policy.md` — bleach allowlists, rel nofollow/noopener, invented-link suppression, language-* classes.
- `./thread-title-scraping.md` — ancestors-then-up h1 walk from #isso-thread with data-title/data-isso-id overrides.

Notifications & extensions
- `./signal-extension-bus.md` — iterable-subscriber Signal and the full comments.* event set.
- `./smtp-reply-fanout.md` — opt-in sibling+parent audience with five-condition exclusion guard.
- `./list-unsubscribe-header.md` — self-describing ("unsubscribe", email) tokens in mail headers.
- `./smtp-retry-senders.md` — uWSGI spooler vs start_new_thread range(5) connect-retry dispatch.
- `./moderation-purge-loop.md` — purge-after sweeper sharing the writer lock across mixins.
- `./session-key-signer.md` — DB-persisted random signing key and every payload shape it carries.

Deployment & import
- `./runtime-cache-mixins.md` — NullCache/SimpleCache/uWSGICache behind one namespace-dropping facade.
- `./origin-negotiation.md` — closed allowlist Origin/Referer reflection for credentials-true CORS.
- `./cors-suburi-stack.md` — make_app wrapper order: local→SharedData→CORS→SubURI→ProxyFix(x_prefix).
- `./config-parser-dialect.md` — timedelta ints, getlist/getiter, expandvars, load-time typo linting.
- `./curl-outbound-client.md` — never-raising httplib wrapper with path-only 301 retry.
- `./title-fetch-on-create.md` — locked check-and-create thread with origin-validated page scrape fallback.
- `./disqus-import-remap.md` — chronological dsq:id→integer remap with post-GC orphan report.
- `./wordpress-import-fixpoint.md` — deferred-worklist insertion with for-else termination bail.
- `./import-dispatch-autodetect.md` — one-buffer format sniffing, guard-off bulk imports, non-empty prompt.
- `./feed-conditional-etag.md` — head-comment etag/last-modified conditional Atom feeds.
- `./multisite-dispatch.md` — name-keyed app mounting and the X-Script-Name pop trap.

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
isso (MIT), `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory project **`isso`** (root `$REFERENCE_ROOT/isso`, branch master, FULL, 1,756n/5,364e, generation 2026-08-26T01:41Z; parse_partial confined to SCSS/nginx/sample cfg/docs/templates — none cited). History: pass 1 mined 45 capsules against the now-retired twin project `ext-isso` @ `$REFERENCE_ROOT/external/isso` at the IDENTICAL HEAD (suite executed GREEN 118/118 via uv venv on 2026-08-24); pass 2 re-established the graph as short-name project `isso` and verified pin parity — older capsules' `project: "ext-isso"` Retrieve calls should substitute `isso`.

## Full view (memory graph)
Revalidate `isso` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Pass-2 coverage stdin sweep ×5 newly cited paths (`isso/__init__.py`, `isso/wsgi.py`, `isso/core.py`, `contrib/dump_comments.py`, `isso/tests/test_wsgi.py`) all `no_recorded_issue` + `metadata_match`; pass 1 recorded a 23-path clean sweep at the same HEAD.

## Boundaries
Adopt the pure contracts: mode-masked visibility, tombstone GC, token-shape discipline, origin allowlisting, anonymize-at-ingestion, event-bus lifecycle. Adapt SQLite spellings, cookie/header names, thresholds, and template plumbing to your host. Omit isso-specific product surfaces: the JS embed client (`isso/js`), demo page, admin HTML templates, and packaging scripts.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`add-maxid-readback.md`](./add-maxid-readback.md)
- [`admin-listing-plane.md`](./admin-listing-plane.md)
- [`app-assembly-order.md`](./app-assembly-order.md)
- [`approved-author-fastpath.md`](./approved-author-fastpath.md)
- [`cli-bootstrap-ladder.md`](./cli-bootstrap-ladder.md)
- [`config-parser-dialect.md`](./config-parser-dialect.md)
- [`cookie-samesite.md`](./cookie-samesite.md)
- [`cors-suburi-stack.md`](./cors-suburi-stack.md)
- [`csrf-json-gate.md`](./csrf-json-gate.md)
- [`curl-outbound-client.md`](./curl-outbound-client.md)
- [`dispatch-error-funnel.md`](./dispatch-error-funnel.md)
- [`disqus-import-remap.md`](./disqus-import-remap.md)
- [`dump-comments-export-plane.md`](./dump-comments-export-plane.md)
- [`edit-cookie-shape.md`](./edit-cookie-shape.md)
- [`feed-conditional-etag.md`](./feed-conditional-etag.md)
- [`guard-limits.md`](./guard-limits.md)
- [`hash-cache-invalidation.md`](./hash-cache-invalidation.md)
- [`hidden-replies-ledger.md`](./hidden-replies-ledger.md)
- [`import-dispatch-autodetect.md`](./import-dispatch-autodetect.md)
- [`input-verification-whitelist.md`](./input-verification-whitelist.md)
- [`karma-mode-mask.md`](./karma-mode-mask.md)
- [`latest-deque.md`](./latest-deque.md)
- [`list-unsubscribe-header.md`](./list-unsubscribe-header.md)
- [`markup-render-selection.md`](./markup-render-selection.md)
- [`migration-ladder.md`](./migration-ladder.md)
- [`moderation-confirm-modal.md`](./moderation-confirm-modal.md)
- [`moderation-purge-loop.md`](./moderation-purge-loop.md)
- [`moderation-token-twin.md`](./moderation-token-twin.md)
- [`multisite-dispatch.md`](./multisite-dispatch.md)
- [`nesting-flatten-migration.md`](./nesting-flatten-migration.md)
- [`origin-negotiation.md`](./origin-negotiation.md)
- [`orphan-trigger.md`](./orphan-trigger.md)
- [`parent-reanchor.md`](./parent-reanchor.md)
- [`remote-addr-trusted-proxy.md`](./remote-addr-trusted-proxy.md)
- [`runtime-cache-mixins.md`](./runtime-cache-mixins.md)
- [`sanitizer-link-policy.md`](./sanitizer-link-policy.md)
- [`session-key-signer.md`](./session-key-signer.md)
- [`signal-extension-bus.md`](./signal-extension-bus.md)
- [`smtp-reply-fanout.md`](./smtp-reply-fanout.md)
- [`smtp-retry-senders.md`](./smtp-retry-senders.md)
- [`socket-server-unix-ladder.md`](./socket-server-unix-ladder.md)
- [`soft-delete-cascade.md`](./soft-delete-cascade.md)
- [`sqlite-execute-per-call.md`](./sqlite-execute-per-call.md)
- [`thread-title-scraping.md`](./thread-title-scraping.md)
- [`threaded-orderby.md`](./threaded-orderby.md)
- [`title-fetch-on-create.md`](./title-fetch-on-create.md)
- [`unsubscribe-scope.md`](./unsubscribe-scope.md)
- [`vote-blob-cap.md`](./vote-blob-cap.md)
- [`wordpress-import-fixpoint.md`](./wordpress-import-fixpoint.md)
