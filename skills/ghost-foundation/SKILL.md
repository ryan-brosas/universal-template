---
name: ghost-foundation
description: "Use when porting Ghost's outbound webhook dispatch engine (HMAC signing, 410 tombstones, SSRF client selection, plan-limit suppression), scheduled-publishing machinery (JWT-signed schedule URLs, in-memory wake ladder, tolerance-based publish decisions), admin session/API-key auth planes (origin-pinned CSRF, email MFA challenges, kid-addressed JWT verification), or the lazy URL service (per-call URL resolution/generation with derived required-shape inference, NQL filter compatibility stripping, thin-resource degrade reporting, canonical reverse lookup, boot readiness gating). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# Ghost: publishing-platform foundation

## Use this for
Use when porting Ghost's outbound webhook dispatch engine (HMAC signing, 410 tombstones, SSRF client selection, plan-limit suppression), scheduled-publishing machinery (JWT-signed schedule URLs, in-memory wake ladder, tolerance-based publish decisions), admin session/API-key auth planes (origin-pinned CSRF, email MFA challenges, kid-addressed JWT verification), or the lazy URL service plane that replaced Ghost's precomputed URL cache — per-call resolution/generation over router configs registered at boot. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/webhook-hmac-envelope.md` — how are outgoing webhook deliveries signed so verifiers accept them byte-exact?
- `references/webhook-client-ssrf-selection.md` — which HTTP client delivers webhooks and why do two exist?
- `references/webhook-410-tombstone.md` — when does a failed delivery delete the subscription itself?
- `references/webhook-limit-funnel.md` — how are third-party webhooks suppressed without breaking internal ones?
- `references/webhook-registration-ladder.md` — how does dispatch subscribe to model events exactly once?
- `references/webhook-dual-serialization.md` — how does one payload carry both current and previous state?
- `references/webhook-composition-root.md` — why is the dispatch pipeline assembled inside listen()?
- `references/webhook-add-validation.md` — how is duplicate registration and dangling integration rejected?
- `references/event-registry-once-guard.md` — why does the event bus need hasRegisteredListener?
- `references/scheduler-token-expiry-window.md` — how long is a scheduler publish URL valid?
- `references/scheduler-event-ladder.md` — how do schedule/unschedule/reschedule map to adapter calls?
- `references/scheduler-default-wake-ladder.md` — how does an in-memory scheduler hit publish times within a second?
- `references/publish-tolerance-ladder.md` — when must a fired schedule job publish, no-op, or refuse?
- `references/schedule-url-auth.md` — how does a scheduler ping authenticate without the 5-minute JWT cap?
- `references/scheduler-error-capture.md` — how do unawaited schedule/unschedule failures get reported without stalling boot?
- `references/internal-keys-autofilling-map.md` — how do in-process integrations get their API keys without per-request lookups?
- `references/session-verification-carryover.md` — when does a fresh login inherit trusted-device status?
- `references/session-csrf-origin-pin.md` — how are cookie-authenticated admin requests bound to the admin origin?
- `references/email-mfa-challenge-lifecycle.md` — what prevents an emailed 6-digit code from verifying another session?
- `references/session-store-contract.md` — what must a custom express-session Store implement over app models?
- `references/admin-apikey-jwt.md` — what is the exact verification order for Admin-API Ghost tokens?
- `references/outbound-ssrf-defense.md` — how is a user-supplied URL prevented from reaching private networks?
- `references/stripe-webhook-intake.md` — what status-code protocol does the inbound Stripe receiver implement?
- `references/stripe-endpoint-reconcile.md` — how does the remote Stripe endpoint stay provisioned across reconnects?
- `references/identity-token-minting.md` — how are members handed short-lived RS256 tokens?
- `references/url-required-shape-inference.md` — which columns/relations must a routable record carry before URL math is legal?
- `references/url-filter-eval-compat.md` — how do routes.yaml NQL filters evaluate without changing legacy routing semantics?
- `references/url-forward-resolution-ladder.md` — how does a resource become exactly one URL, and who wins router conflicts?
- `references/url-thin-resource-degrade-pact.md` — what happens when a caller under-fetches the record it asks a URL for?
- `references/url-reverse-canonical-resolve.md` — how does a request path resolve to exactly one resource without false positives?
- `references/url-boot-registration-readiness.md` — how does the service come alive, survive route reloads, and hold the site during the gap?
- `references/url-routable-enumeration-batching.md` — how do you list every routable row without loading the table or tripping driver limits?

## Capsule map
- **Webhook dispatch** — `webhook-hmac-envelope`: HMAC-SHA256 over exact body bytes + decimal ms timestamp, header `X-Ghost-Signature: sha256=<mac>, t=<ts>`; empty secret ⇒ no header; 2s timeout, retry 5 (0 in tests).
- **SSRF client choice** — `webhook-client-ssrf-selection`: injected client wins; `security:allowWebhookInternalIPs` ⇒ plain request lib; default is SSRF-filtered request-external.
- **Delivery lifecycle** — `webhook-410-tombstone`: only HTTP 410 deletes the webhook row; every other outcome writes last_triggered_* fire-and-forget; telemetry failures never throw into the event bus.
- **Plan limits** — `webhook-limit-funnel`: two-stage gate (`isLimited` then `checkWouldGoOverLimit`) filters post-fetch to internal integrations only — same query both paths.
- **Event wiring** — `webhook-registration-ladder`: 29 declared events, named-listener once-guard, import-suppression via options, unawaited trigger.
- **Payload shape** — `webhook-dual-serialization`: `{<singular>: {current, previous}}` from dual API serialization; load only MISSING url-service relations; changed-key diff happens in serialized key space with rename map.
- **Pipeline assembly** — `webhook-composition-root`: factories closed over deps, singletons required inside listen() because models must not load before boot wires them.
- **Inbound validation** — `webhook-add-validation`: (event, target_url) pre-check plus MySQL errno 1452 / two SQLite FK shapes translated to one ValidationError.
- **Bus hygiene** — `event-registry-once-guard`: reboot-in-same-process duplicates are killed by matching NAMED listener functions, not identity.
- **Schedule tokens** — `scheduler-token-expiry-window`: exp = published_at+6h floored at now+6h, nbf = −10min, `noTimestamp:true`, hex-decoded HS256 secret.
- **Adapter contract** — `scheduler-event-ladder`: reschedule = unschedule(prev-time-signed) + schedule(current); boot rebuild passes `{bootstrap:true}` so same-key unschedule skips tombstone poisoning.
- **Wake ladder** — `scheduler-default-wake-ladder`: <10min executes now; others wake diff−70ms then setImmediate-spin to −50ms; counted tombstones; 404 no-op, 503 retries ×30 @5s; past publish adds force flag.
- **Publish decision** — `publish-tolerance-ladder`: >tolerance early ⇒ 2xx NO_OP; <−tolerance without force ⇒ NotFoundError; deleted resource ⇒ NO_OP; cache-invalidate `/*` on real publishes.
- **Schedule auth** — `schedule-url-auth`: token from URL query with `ignoreMaxAge` (exp/nbf already bound); permission + query stages both swallow only NotFoundError.
- **Boot safety** — `scheduler-error-capture`: decorator reports sync throws AND rejected promises from schedule/unschedule; logs path-only URLs (tokens redacted).
- **Key cache** — `internal-keys-autofilling-map`: promise-valued AutoFillingMap keyed by internal slug; `.clear()` after rotation; single-flight DB fetch.
- **Session trust** — `session-verification-carryover`: verification survives regenerate only as (verified, verified_user_id) pair bound to the SAME user; legacy sessions fail closed.
- **CSRF pinning** — `session-csrf-origin-pin`: request origin must equal admin origin ALWAYS, then equal session.origin after init; explicit bypass flag for OAuth.
- **Email MFA** — `email-mfa-challenge-lifecycle`: per-session rotating TOTP challenge, 5-min validity, single-use invalidation; Needs2FA codes distinguish policy-MFA from new-device.
- **Store contract** — `session-store-contract`: Store subclass over model upsert; missing row = callback(null,null) not error.
- **Admin keys** — `admin-apikey-jwt`: unverified decode → kid → DB ApiKey → type check → pinned HS256 + maxAge 5m + audience regex from originalUrl → verify last.
- **Outbound defense** — `outbound-ssrf-defense`: beforeRequest DNS check + authoritative connection-time dnsLookup gate re-applied on every redirect; fail-closed normalization of octal/hex/integer/mapped hosts.
- **Stripe intake** — `stripe-webhook-intake`: 400 missing sig, 401 bad sig, ignore-listed customers 200 on subscription.updated only, unknown types silently 200, handler errors err.statusCode||500.
- **Endpoint reconcile** — `stripe-endpoint-reconcile`: update→recreate ladder; resource_missing skips delete; config-secret local mode never provisions remotely.
- **Identity plane** — `identity-token-minting`: RS256 sub=email (+role?) 5-minute bearer for cross-subdomain member verification — asymmetric contrast to admin keys.
- **Required shape** — `url-required-shape-inference`: getRequiredFields/getRequiredRelations derive columns+relations from live router configs; boundary-anchored field regex so timestamp VALUES aren't fields; primary_* computed attrs forced like scalars; memoized until config changes.
- **Filter compat** — `url-filter-eval-compat`: one NQL evaluator (expansions + page:true/false→type transformer) for forward/ownership/reverse; lazy parse means buildFilter('((') compiles and the catch→warn+false is the only guard; legacy exclude-list columns stripped before router-filter match (absent=NQL null) and never required.
- **Forward ladder** — `url-forward-resolution-ladder`: type normalize → base gate only if a router exists → priority-ordered first-match filter scan → replacePermalink → format; /404/ formatter must not pass createUrl's trailingSlash arg; ownsResource mirrors base gate + exclusive first owner.
- **Thin degrade** — `url-thin-resource-degrade-pact`: under-fetched record ⇒ report keyed resourceType|router|missing|endpoint, log at powers of ten, silent /404/, never throw (unexpected throws propagate); serializers force required fields+relations+id on input and strip after output.
- **Reverse resolve** — `url-reverse-canonical-resolve`: token whitelist + hyphen-bounds (#28076) + format prefilter + %-escape nulls → minimal id-over-slug lookup with per-call memo → filter re-check → canonical URL regeneration must equal captured params; findResource scoping mirrors base filters.
- **Boot readiness** — `url-boot-registration-readiness`: singleton `new LazyUrlService({findResource})` fails fast; initDynamicRouting runs on backend-only boots too or every API URL 404s; registration order = ownership priority; reset() reopens the maintenance 503 window via hasFinished().
- **Enumeration** — `url-routable-enumeration-batching`: include→exclude translation against table schema; shouldHavePosts joins keep empty tags/staff unlisted; relations pinned to id+slug only when routing reads them; SQLite batches of 999 ordered by id (#5810).

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Ghost (MIT). Pass 1 mined webhook/scheduler/auth/Stripe capsules under Codebase Memory project `ext-ghost` (root `/mnt/hdd/utopia/inspo/external/ghost`, generation 2026-08-23T09:41:18Z, 92,856 nodes / 267,193 edges) — that project is no longer in the registry. Pass 2 (2026-08-26, FAC-197) re-pointed this leaf at live project `ghost` (root `/mnt/hdd/utopia/inspo/ghost`, FIRST-RUN FULL index, same pin): branch `main`, head==base==`81292b004cf59591f03d7dbe01f28f31c09ee813` = zero drift, generation `2026-08-26T01:41:39Z` generation_matches=true, 92,856 nodes / 267,137 edges, skipped=0, parse_partial ×42 confined to CSS/YAML fixtures/pnpm-lock (none cited), not_indexed ×714 by design. check_index_coverage ×16 pass-2 paths all `no_recorded_issue` + `metadata_match`. Legacy ext-ghost Retrieve snippets should be replayed against project `ghost` — identical HEAD means symbols match.

## Full view (memory graph)
Revalidate `ghost` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. BM25 notes: query by exact name first and fall back to file reads — free-function symbols can rank low (publishAPostBySchedulerToleranceInMinutes surfaces under handleCacheInvalidation queries); naive natural-language questions miss the URL-service seams entirely ("map request url path to post resource" surfaced admin helpers + lazy-find-resource only), so use the capsule vocabulary above.

## Boundaries
Adopt the pure contracts (signature envelope, 410 tombstone, tolerance ladder, token windows, verification order, once-guard registration, capture-decorator reporting, lazy URL resolution ladders, thin-resource degrade policy, canonical reverse confirmation); adapt express-session/Bookshelf/got plumbing, the Bookshelf event bus, NQL filter compilation, and route shells to your host stack; omit Ghost product surfaces (themes, Koenig editor, portal/signup apps, Ember admin, ActivityPub app) and the Docker dev harness.
