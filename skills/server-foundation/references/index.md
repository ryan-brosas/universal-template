<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Bitwarden server: push-notification platform foundation

## Use this for
Use when porting multi-engine push/notification fan-out, Azure Notification Hubs registration pools, tag-based targeting/exclusion grammars, installation-relay protocols for self-hosted instances, feature-flagged per-user vault-sync fan-out, or the real-time consumer side: SignalR hub group grammars and connect lifecycles, queue-consumer poll/poison loops, internal send ingress, wire-format contract tables across rolling deploys, and pre-auth token-as-group waiting rooms. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./multiservice-fire-forget-fanout.md` — how one notification reaches every engine without failing the caller.
- `./hub-pool-comb-sharding.md` — deterministic device→hub routing with time-windowed registration admission.
- `./hub-tag-grammar.md` — how template tags encode target/exclusion/client-type on the send path.
- `./relay-endpoint-guards.md` — what a self-host→cloud relay receive endpoint must enforce.
- `./registration-templates-tag-patch.md` — cross-platform install registration and org-tag patching without full rewrite.
- `./cipher-sync-flagged-fanout.md` — flag-gated org-cipher fan-out that degrades to non-mobile-only delivery.
- `./hub-group-grammar-connect-lifecycle.md` — SignalR group naming grammar and mirrored connect/disconnect membership.
- `./queue-consumer-poison-pill-poll-loop.md` — inert-start gate, bounded redelivery poison drop, and the WhenAny stop ladder.
- `./dual-dialect-wire-contract-tables.md` — producer-replayed RoutingCase tables keeping queue + HTTP ingestion format-safe across rolling deploys.
- `./hubhelpers-type-switch-routing.md` — discriminator-peek then typed-reparse routing over inner payload fields.
- `./anonymous-token-as-group-hub.md` — pre-auth devices listening on a server-minted id as the group name.

## Capsule map
- **Fan-out kernel** — `multiservice-fire-forget-fanout`: Release-mode fan-out discards per-engine tasks; only DEBUG awaits them.
- **Hub pool** — `hub-pool-comb-sharding`: warn-not-throw config filter, comb-time window admission, hash-bin hub selection with diagnostic throw.
- **Tag grammar** — `hub-tag-grammar`: `(template:{name}[_userId:{id}] && !deviceIdentifier:{san} && clientType:{t})` byte-exact contract.
- **Relay guards** — `relay-endpoint-guards`: cloud-only gate, `{installationId}_` identifier namespacing, Installation-match > User > Org trichotomy; full-range integration evidence (real installation OAuth, zero queue writes, device-entity upserts).
- **Registration** — `registration-templates-tag-patch`: 3-template mobile installs, REST web-push fallback, ADD-vs-REMOVE `/tags` patch asymmetry, 404-swallow filter.
- **Cipher sync** — `cipher-sync-flagged-fanout`: flag-off ⇒ org-target NonMobileOnly; flag-on ⇒ deduped collection ids → per-user Task.WhenAll with loud empty-skip; full-range test evidence incl. SyncLoginDelete quirk.
- **Hub groups** — `hub-group-grammar-connect-lifecycle`: static group-name builders, claim rebuild per connect/disconnect event, client-type as a name axis, `sub`-claim user-id provider.
- **Queue consumer** — `queue-consumer-poison-pill-poll-loop`: unconfigured ⇒ no loop task at all; DequeueCount>2 poison delete; TimeProvider idle delay; shutdown race that rethrows only on host cancellation.
- **Wire contracts** — `dual-dialect-wire-contract-tables`: PascalCase/no-nulls queue vs camelCase/explicit-nulls `/send`; ≥1-release old-entry retention; never add entry + handler in one commit.
- **Router** — `hubhelpers-type-switch-routing`: envelope peek + per-family re-deserialization; drop-with-warning default; anonymous-hub escape for auth-request responses.
- **Pre-auth wait room** — `anonymous-token-as-group-hub`: AllowAnonymous hub where the query token IS the group name; safe only because ids are server-minted GUIDs.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Bitwarden server (AGPL-3.0 default per LICENSE.txt L1–L5; Bitwarden License v1.0 confined to /bitwarden_license/, not cited), `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory project `server` (FULL index this pin, 80,796 nodes / 489,085 edges, gen 2026-08-25T19:57:48Z; parse_partial caveats: MultiServicePushNotificationService.cs :53/:57 read directly, T-SQL/.ps1 files uncited). Pass 1 mined the producer plane (6 capsules); pass 2 mined the src/Notifications consumer plane (+5 capsules) and upgraded relay/cipher probes to full-range test reads.

## Full view (memory graph)
Revalidate `server` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: envelope record shape (`PushType`+target+payload+ExcludeCurrentContext), fire-and-forget multi-engine fan-out semantics, comb-guid sharded pool with registration windows, tag grammar, relay guard ladder, template/tag-patch registration contracts, flagged fan-out degradation, hub group-name grammar, queue-consumer lifecycle ladder, RoutingCase wire-evolution discipline, discriminator-peek routing. Adapt transport details (Azure Queue/Notification Hubs SDK calls, Redis backplane gate, MessagePack contractless resolver setup, Identity client-service auth) to your host's brokers. Omit Bitwarden product behavior: PushType enum values' client meanings, NotificationCenter DB-status domain plane, Quartz job scheduling details, and the transient `NonMobileOnly` flag mechanics tied to their rollout.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`anonymous-token-as-group-hub.md`](./anonymous-token-as-group-hub.md)
- [`cipher-sync-flagged-fanout.md`](./cipher-sync-flagged-fanout.md)
- [`dual-dialect-wire-contract-tables.md`](./dual-dialect-wire-contract-tables.md)
- [`hub-group-grammar-connect-lifecycle.md`](./hub-group-grammar-connect-lifecycle.md)
- [`hub-pool-comb-sharding.md`](./hub-pool-comb-sharding.md)
- [`hub-tag-grammar.md`](./hub-tag-grammar.md)
- [`hubhelpers-type-switch-routing.md`](./hubhelpers-type-switch-routing.md)
- [`multiservice-fire-forget-fanout.md`](./multiservice-fire-forget-fanout.md)
- [`queue-consumer-poison-pill-poll-loop.md`](./queue-consumer-poison-pill-poll-loop.md)
- [`registration-templates-tag-patch.md`](./registration-templates-tag-patch.md)
- [`relay-endpoint-guards.md`](./relay-endpoint-guards.md)
