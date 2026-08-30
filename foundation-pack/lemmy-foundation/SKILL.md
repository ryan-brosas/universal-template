---
name: lemmy-foundation
description: "Use when building federation/dispatch engines: per-peer DB-backed activity queues with exactly-once cursors, exponential backoff shared across concurrent senders, modulo-sharded worker fleets, community inbox fan-out maps, Announce wrapping, signed inbound receive gates with dedup, and cross-vendor object round-trips."
disable-model-invocation: true
---

# Lemmy: federation protocol & dispatch engine

## Use this for
Use when porting an ActivityPub-style federation stack or any multi-subscriber outbound dispatcher: durable per-recipient delivery queues on plain SQL, ordered at-least-once sends with crash resume, retry ladders that don't melt under concurrent failures, interest-map fan-out (who cares about which event), envelope-wrapped group broadcasts, signed inbound processing with once-only stamps, private-content read authorization across trust boundaries, and lossless wire-object round-trips against heterogeneous clients. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/instance-send-queue-worker.md` — one worker per remote peer turns a global monotone activity table into a gapless, crash-resumable delivery stream with a min-heap reorder buffer.
- `references/instance-lifecycle-policy.md` — peer state machine: allow∧¬block∧¬dead gates worker existence; successful sends refresh liveness ≤1 write/day; host bans checked at person verification.
- `references/federation-retry-backoff.md` — 1.25^n capped backoff where N simultaneous failures count as ONE step; remaining-duration sleep resume after crashes.
- `references/community-inbox-collector.md` — per-subscriber interest map kept fresh by hourly full-replace + 2-minute overlapping-watermark incremental.
- `references/send-manager-sharding.md` — stateless horizontal scale-out via `instance_id % process_count`, map-reconcile worker lifecycle, restart-on-error task wrapper.
- `references/sent-activity-outbox.md` — transactional outbox row carrying payload + three-way routing metadata + serial id as delivery order; weak-sender channel in front.
- `references/shared-inbox-dispatch-ladder.md` — recipient decision ladder: visibility gate → direct inboxes → user followers (non-mod) → local Announce OR forward to hosting community.
- `references/announce-wrapper.md` — lossless raw-payload envelope, single-announcer re-wrap rule, no-local-interest refuse gate, dual-format compat emit for limited parsers.
- `references/delete-verification-matrix.md` — per-type destructive-action authorization (mod vs owner vs self), domain-equality ownership proof, idempotent flag application, re-echo by owner.
- `references/shared-inbox-receive-gate.md` — signature → once-only received-activity stamp → typed verify/receive, all under a deadline SHORTER than peers' client timeout.
- `references/federation-state-durability.md` — 60 s bounded-staleness cursor checkpointing with failure-forced early writes and final flush on shutdown = deliberate at-least-once.
- `references/moka-single-flight-caches.md` — try_get_with coalescing: immutable-entity no-TTL caches + unit-key TTL cache as a process-wide rate limiter.
- `references/private-community-fetch-auth.md` — instance-granularity read authorization for private content: local follower table or signed SSRF-guarded back-check to the source.
- `references/follow-accept-handshake.md` — Follow/Accept/Undo lifecycle correlated by original activity id, typed refusals, approval-pending states, new-subscriber content priming.
- `references/vote-activity-semantics.md` — transition-diffed event emission: no-op short-circuit, direction-carrying summary field, direction-matched Undos only.
- `references/apub-object-roundtrip.md` — DB row ≠ wire DTO: flatten-extra lossless deserialization, Either-typed polymorphic fields, cross-vendor fixture corpus as parse suite.

## Capsule map
- **Send queue** — `instance-send-queue-worker`: persisted `{last_successful_id, fail_count}` per peer; claim `cursor+1`; prefix-only commit through a min-heap of out-of-order successes; internal errors become skips so one bad activity never stalls a peer.
- **Failure policy** — `federation-retry-backoff`: task-local counter reports monotone `fail_count`, worker keeps max (concurrent failures collapse), success decrements; curve 0 s → 1.25^n s → DAY cap.
- **Fan-out map** — `community-inbox-collector`: HashMap<CommunityId, HashSet<InboxUrl>> per receiving instance; removals ONLY via hourly full replace; additions via half-interval-overlap watermark query; zero-target result avoids spawning the send task at all.
- **Scale-out** — `send-manager-sharding`: pure modulo sharding over the entity PK replaces distributed locks; CancellableTask restarts errored loops forever unless cancelled; shutdown cancels all workers concurrently within a 30 s grace.
- **Peer lifecycle** — `instance-lifecycle-policy`: worker existence = allowlist ∧ ¬blocklist ∧ ¬dead; deadness derives from `updated_at` staleness which successful sends refresh at ≤1 write/day/peer; `InstanceActions::check_ban` enforces host-level bans on every person verification.
- **Durable hand-off** — `sent-activity-outbox`: API threads enqueue typed intents on an unbounded channel (weak sender = kill switch); the consumer serializes to one `sent_activity` row whose serial id IS global order; `sensitive` flags GET exposure.
- **Routing** — `shared-inbox-dispatch-ladder`: unfederable visibility ⇒ silent no-op; mod actions skip user-follower fan-out; exactly ONE instance announces group events (the host); reports additionally hit moderators + both home instances.
- **Broadcast envelope** — `announce-wrapper`: nested raw inner activity (unknown fields preserved), accept gate requiring local follows/posts/comments for remote communities, Page-only compat second send for Mastodon/Pleroma.
- **Destructive actions** — `delete-verification-matrix`: type-keyed verify ladder (community=mod-only, person=self-only+URL-equal, post/comment=mod OR same-origin-owner, PM=domain-match); conditional updates make re-delivery idempotent; receivers re-echo deletions they own.
- **Inbound gate** — `shared-inbox-receive-gate`: POST guard filters non-AP traffic; hook stamps every received id once (`on_conflict_do_nothing`, duplicate ⇒ reject); whole receive wrapped in a 9 s timeout because the peer's HTTP client times out at 10 s and would mark us dead.
- **Crash semantics** — `federation-state-durability`: cursor persists ≤60 s stale (failure bookkeeping forces immediate writes); graceful exit upserts once more; at-least-once is the CONTRACT, receiver dedup is the counterpart.
- **Caching** — `moka-single-flight-caches`: actors/activities cached without TTL because AP ids+keys are immutable; `Cache<(), _>` unit key throttles max(id) probes to 1/s fleet-wide; try_get_with gives per-key single-flight.
- **Trust boundary reads** — `private-community-fetch-auth`: Private ⇒ resolve signing actor's INSTANCE; local communities answer from the approved-follower table; mirrored communities get a signed, SSRF-checked probe of the source's followers URL; deny = NotFound.
- **Subscriptions** — `follow-accept-handshake`: Accept embeds the follow's exact id; restricted-community follows are refused with typed errors; fresh followers are primed with the newest post before the next broadcast.
- **Reactions** — `vote-activity-semantics`: `(previous, new)` diff drives Vote/Undo/no-op; direction rides an optional `summary` field; Undos must match direction or error.
- **Wire contract** — `apub-object-roundtrip`: ecosystem-shaped protocol structs with flattened extras + Either-typed fields keep every vendor's content parseable while DB rows keep raw text AND rendered HTML.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question (candidates: block/ban activity plane `crates/apub/activities/src/block/`, collection paging `crates/apub/apub/src/collections/community_outbox.rs`, markdown link/mention rewriting `crates/apub/objects/src/utils/{markdown_links,mentions}.rs`, report/warn plane, person/site fetch-timeout handling). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
lemmy (AGPL-3.0), `main@439734dd638a2c06a2f907beab7dcf4646e88f86` (= base_sha, first pass); Codebase Memory project `ext-lemmy` (ready, root `/mnt/hdd/utopia/inspo/external/lemmy`, branch main@same sha, 14,551 nodes / 54,374 edges, HEAD==base zero drift; parse_partial = SQL/Dockerfile/nginx files only — no cited .rs path affected; skipped = 0; not_indexed = .git BY DESIGN).

## Full view (memory graph)
Revalidate `ext-lemmy` before porting: run `index_status --project ext-lemmy --verbose`, `check_index_coverage` (stdin JSON), `search_graph`, `trace_path`, `get_code_snippet`. Root `/mnt/hdd/utopia/inspo/external/lemmy`, branch `main@439734dd`, 14,551 nodes / 54,374 edges. All 18 cited source paths reported `no_recorded_issue` + generation match on check_index_coverage at this pin. Graph symbol resolution verified live for `loop_until_stopped`, `handle_send_results`, `pop_successfuls_and_write`, `spawn_send_if_needed`, `send_retry_loop`, `get_inbox_urls`, `update_communities`, `check_accept_activity_in_community`, `get_instance_followed_community_inboxes`, `shared_inbox`. Direct tests live in-file (`crates/apub/send/*` actix test servers + mockall collector suite, `crates/db_schema/src/impls/activity.rs`) plus ~14-vendor JSON fixture corpora under `crates/apub/apub/assets/`. Rust test runner not executed this pass (no DB/toolchain in inspo clone) — probes verified byte-exact as deterministic greps; no fabricated pass.

## Boundaries
Adopt the DB-as-queue cursor protocol, shared-counter backoff, modulo sharding, interest-map fan-out with dual-cadence refresh, single-announcer announce rule, once-only inbound stamping with sub-peer-timeout deadlines, instance-granularity private-read auth, and transition-diffed event emission. Adapt Rust/tokio idioms, moka specifics, ActivityPub wire vocabulary, Postgres/diesel plumbing, and Lemmy's domain objects (posts/comments/communities) to your host — the contracts port, the types don't have to. Omit the web UI, the api/routes product surface, db_views query builders, pictrs/media handling, email/notification planes, and rate-limit middleware (unmined this pass).
