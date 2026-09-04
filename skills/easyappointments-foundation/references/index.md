<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Easy!Appointments Foundation

## Use this for
Use when porting a scheduling engine's availability computation (working plans, breaks, exceptions, unavailabilities, blocked periods), group-service slot capacity, booking conflict enforcement, webhook fan-out, or the auth/permission scaffolding around a multi-role booking UI. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./interval-subtraction-ladder.md` — carve booked time out of a provider's day: five-case overlap grammar, exception-replaces-plan rule.
- `./break-removal-four-case.md` — in-place break/unavailability subtraction twins with fragment chaining.
- `./multi-attendant-group-slots.md` — sliding-window slots for group services; same-service counts, other-service vetoes.
- `./provider-tz-booking-windows.md` — book-advance timeout + future booking limit thresholds in provider timezone, terminal sort.
- `./conflict-gate-two-grammars.md` — save-time strict overlap predicate vs boundary-shifted slot counting; UI gate vs API permissiveness.
- `./any-provider-resolution.md` — `'any-provider'` sentinel → max-free-hours provider ranking with hour filter.
- `./webhook-dispatcher.md` — comma-action matching, custom secret header envelope, swallow-and-log synchronous delivery, `is_active` trap.
- `./api-dual-auth.md` — timing-safe bearer token → admin-gated Basic → 401 challenge ladder with multi-source header reading.
- `./customer-access-scoping.md` — appointment-relationship-derived customer visibility with one-hop secretary delegation.
- `./permission-bitmask-ladder.md` — 1/2/4/8 view/add/edit/delete decode highest-bit-first; deliberate add/edit swap on save paths.
- `./two-tier-rate-limiting.md` — global 100/120s per-IP limiter vs login 5/300s counter; fail-closed vs fail-open postures.
- `./login-hardening-ladder.md` — charset allowlist, DB→LDAP fallback, randomized uniform failures, delete-on-regenerate sessions.
- `./legacy-hash-migration.md` — bcrypt cost 12 with lazy upgrade of iterated-SHA-256 legacy hashes on successful login.
- `./best-effort-sync-fanout.md` — Google/CalDAV mirror-id-keyed create/update with immediate write-back and log-and-continue errors.
- `./retention-cleanup.md` — retention purge predicate (no live/future appointments AND old enough), per-row failure isolation.
- `./api-resource-mapping.md` — camelCase↔snake_case maps, two-gate ORDER BY sanitization, keyExists-guarded partial decodes.
- `./session-reconciliation-boot.md` — every-request session-vs-DB reconciliation plus the global rate-limit call in EA_Controller.

## Capsule map
- **Availability kernel** — `interval-subtraction-ladder`: `get_available_periods` merges appointments+unavailabilities+blocked periods then subtracts via five overlap cases (left-trim / inside-split / exact-equal unset / right-trim / superset unset); date regex-gated; working-plan exception REPLACES the weekday plan before any math.
- **Break plane** — `break-removal-four-case`: `remove_breaks`/`remove_unavailability_events` mutate periods by reference through left/middle(append-right)/right/contains cases; appended fragments are iterated so chained blockers still resolve; public methods reused cross-path.
- **Group services** — `multi-attendant-group-slots`: attendants>1 path builds one period from plan/exception, strips breaks+unavailability+blocked, slides a duration window by slot_interval (default 15m); other-service appointments veto a slot outright while same-service count must stay below attendants_number.
- **Booking windows** — `provider-tz-booking-windows`: advance-timeout drops hours ≤ now+N minutes and future-limit zeroes dates beyond now+M days, both computed in the provider's timezone with max(0) clamps, output re-indexed and string-sorted ascending.
- **Conflict enforcement** — `conflict-gate-two-grammars`: `has_provider_conflict` uses half-open `(start < new_end AND end > new_start)`; the slot counter uses boundary-inclusive pairs instead; Calendar returns `{success:false,conflict:true}` unless force_save; API v1 store() has NO gate by design.
- **Any-provider** — `any-provider-resolution`: string sentinel until register() resolves it by ranking providers on most remaining available hours (strict > keeps first-seen ties) filtered to those offering the requested hour.
- **Webhooks** — `webhook-dispatcher`: trigger() loads ALL webhooks, matches trimmed comma-action lists strictly, POSTs `{action,payload}` with caller-named secret header and per-webhook SSL toggle; delivery is synchronous fail-open logging only — is_active is never checked.
- **API auth** — `api-dual-auth`: hash_equals static bearer token first, then Basic creds that MUST resolve to role_slug admin, else WWW-Authenticate Basic challenge exit; Authorization header read across three server-variable sources.
- **Customer scoping** — `customer-access-scoping`: limit_customer_access makes customer rows visible only via shared appointment history — own rows for providers, one-hop managed-provider fan-out for secretaries, explicit deny otherwise.
- **Permissions** — `permission-bitmask-ladder`: PRIV_VIEW/ADD/EDIT/DELETE = 1/2/4/8 summed per resource column, decoded descending divide-and-subtract into boolean maps; can()/cannot() fail closed; save paths deliberately require add-on-create vs edit-on-update.
- **Rate limiting** — `two-tier-rate-limiting`: file-cache counters keyed by colon-stripped IPs; global limiter exits raw 429 and skips CLI/disabled; login limiter throws JSON-renderable errors but fails open on cache faults.
- **Login hardening** — `login-hardening-ladder`: username charset allowlist + password length cap before credential check; local-then-LDAP backends; identical message plus random 100–300 ms sleep on any failure; sess_regenerate(true) on success.
- **Password crypto** — `legacy-hash-migration`: `$2[ayb]$` prefix sniffs bcrypt (cost 12); non-bcrypt hashes verify against salt-split sha256 iterated 100k× then get lazily rewritten to bcrypt inside the same successful request.
- **Calendar sync** — `best-effort-sync-fanout`: per-provider google_sync/caldav_sync flags drive refresh→create-or-update keyed on mirrored remote ids, ids written back immediately; everything inside catch(Throwable)-log; deletes skip backends without mirror ids.
- **Retention GC** — `retention-cleanup`: customers purged only when role=customer AND no appointment ends after cutoff AND created before cutoff (0 disables); storage tiers glob-delete past STORAGE_RETENTION_DAYS=90 preserving sentinel files.
- **API mapping** — `api-resource-mapping`: $casts/$api_resource per model; api_decode copies mapped keys over an optional base for partial updates; sort params pass TWO gates (whitelist drop + regex/backtick quote) before reaching SQL.
- **Boot guard** — `session-reconciliation-boot`: EA_Controller verifies storage writability, destroys sessions whose user vanished from the DB (403), configures TZ/locale, then applies the global rate limiter last.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question (candidates: CalDAV sync internals in `libraries/Caldav_sync.php`, Google_Sync token refresh chain, Notifications email templating, ICS generation, Timezones conversion helper). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
easyappointments (GPL-3.0 — patterns only, never verbatim), `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory project `ext-easyappointments` (ready, root `/mnt/hdd/utopia/inspo/external/easyappointments`, branch main@same sha, 42,155 nodes / 57,424 edges, FULL mode, indexed gen 2026-08-23T11:45Z generation_matches=true; parse_partial = 88 files, all PHP views/SCSS/config-yaml templates — none cited here; skipped 0; not_indexed = images/fonts BY DESIGN).

## Full view (memory graph)
Revalidate `ext-easyappointments` before porting: run `index_status`, `check_index_coverage` (18 cited paths returned `no_recorded_issue` + `metadata_match` at the pinned generation), `search_graph` (all seam symbols resolve line-exact under BM25), `trace_path`, and `get_code_snippet`. Source and direct tests decide shipped claims: upstream ships only 3 tiny helper unit tests (`tests/Unit/Helper/*`), so every Probe here is a deterministic source pin (grep counts/line anchors verified at pin) and behavior claims carry that caveat.

## Boundaries
Adopt the pure scheduling/auth contracts: interval ladders, capacity queries, overlap predicates, bitmask decode, auth ordering, retention predicate. Adapt CI3-specific plumbing: query-builder chains, `setting()`/`can()` global helpers, session helpers, Guzzle client options. Omit product surface: PHP views/assets, install/update wizards, docker/nginx configs, Google API client details, LDAP server specifics, and the enterprise/Captain-style add-ons absent from this OSS tree.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`any-provider-resolution.md`](./any-provider-resolution.md)
- [`api-dual-auth.md`](./api-dual-auth.md)
- [`api-resource-mapping.md`](./api-resource-mapping.md)
- [`best-effort-sync-fanout.md`](./best-effort-sync-fanout.md)
- [`break-removal-four-case.md`](./break-removal-four-case.md)
- [`conflict-gate-two-grammars.md`](./conflict-gate-two-grammars.md)
- [`customer-access-scoping.md`](./customer-access-scoping.md)
- [`interval-subtraction-ladder.md`](./interval-subtraction-ladder.md)
- [`legacy-hash-migration.md`](./legacy-hash-migration.md)
- [`login-hardening-ladder.md`](./login-hardening-ladder.md)
- [`multi-attendant-group-slots.md`](./multi-attendant-group-slots.md)
- [`permission-bitmask-ladder.md`](./permission-bitmask-ladder.md)
- [`provider-tz-booking-windows.md`](./provider-tz-booking-windows.md)
- [`retention-cleanup.md`](./retention-cleanup.md)
- [`session-reconciliation-boot.md`](./session-reconciliation-boot.md)
- [`two-tier-rate-limiting.md`](./two-tier-rate-limiting.md)
- [`webhook-dispatcher.md`](./webhook-dispatcher.md)
