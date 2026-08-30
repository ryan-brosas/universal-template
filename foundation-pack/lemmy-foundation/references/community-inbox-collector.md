<!-- capsule-v2 -->
# Community inbox collector — which inboxes does a remote instance actually care about, and how do you keep that set fresh cheaply?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** Per-instance senders need "which of MY communities does THIS remote instance follow" — how is that fan-out map maintained with bounded DB load and safe staleness?

## CommunityInboxCollector
**Path/Symbol:** `crates/apub/send/src/inboxes.rs:CommunityInboxCollector` (:81–219, generic over the `DataSource` trait :44–51 so tests inject mocks); production alias `RealCommunityInboxCollector` (:96).
**Signature:** `get_inbox_urls(&mut self, activity: &SentActivity) -> LemmyResult<Vec<Url>>`; `update_communities(&mut self) -> LemmyResult<()>`; backing query `CommunityFollowerView::get_instance_followed_community_inboxes(pool, instance_id, published_since)` (`crates/db_views/community_follower/src/impls.rs:36–60`: `followed_at > published_since`, `DISTINCT (community_id, person.inbox_url)`, filtered to that follower instance).
**Data Shape:** `followed_communities: HashMap<CommunityId, HashSet<Url>>` cached in the worker; two watermarks `last_full_communities_fetch` / `last_incremental_communities_fetch`; consts `FOLLOW_ADDITIONS_RECHECK_DELAY = 2 min` (1 s under `LEMMY_TEST_FAST_FEDERATION`), `FOLLOW_REMOVALS_RECHECK_DELAY = 1 hour` (:30–42).

### Decisive source
```rust
// inboxes.rs:169-192 — dual-cadence refresh: full reload hourly (picks up unfollows),
// incremental extend every 2 minutes (picks up new follows); overlap guards clock skew
if (Utc::now() - self.last_full_communities_fetch) > *FOLLOW_REMOVALS_RECHECK_DELAY {
  (self.followed_communities, self.last_full_communities_fetch) =
    self.get_communities(self.instance_id, Utc.timestamp_nanos(0)).await?;
  self.last_incremental_communities_fetch = self.last_full_communities_fetch;
}
if (Utc::now() - self.last_incremental_communities_fetch) > *FOLLOW_ADDITIONS_RECHECK_DELAY {
  let (news, time) = self.get_communities(self.instance_id, self.last_incremental_communities_fetch).await?;
  self.followed_communities.extend(news);
  self.last_incremental_communities_fetch = time;
}

// inboxes.rs:205 — the watermark is set BEFORE now by half the poll interval so rows written
// during the query can never fall between two fetches
let new_last_fetch = Utc::now() - *FOLLOW_ADDITIONS_RECHECK_DELAY / 2;

// inboxes.rs:149-159 — explicit-target filter: only inboxes on THIS instance's domain survive;
// early empty return avoids spawning the (expensive) tokio send task at all
.filter(|&u| u.domain() == Some(&self.domain))
```

**Flow:** every loop tick calls `update_communities` (full reload ≥ hourly REPLACES the map — the only mechanism that removes stale follows; incremental ≥ 2-min EXTENDS it) → for each activity: `send_all_instances ⇒ target the instance's Site inbox (lazy-loaded; most non-Lemmy software has no site row and simply can't handle these activities, :139–141)`, `send_community_followers_of ⇒ lookup in the cached map`, `send_inboxes ⇒ keep only URLs whose domain equals this instance` → union into a `HashSet`, return; empty result = activity irrelevant to this peer.
**Invariant:** removals propagate only via the hourly FULL replace — an incremental-only design would retain follows forever after unfollow. The half-interval watermark rollback makes the incremental window overlap-safe even with imprecise `published_at`. Domain filtering happens HERE (not just later inside the federation library) so the happy path returns zero URLs and no send task is spawned.
**Probe:** `crates/apub/send/src/inboxes.rs` mockall tests `test_get_inbox_urls_combined` (:397–459 — site + followers + direct inboxes union to exactly 3, foreign-domain user inbox dropped), `test_update_communities` (:463+, full-vs-incremental fetch counting), `test_get_inbox_urls_empty` (:255–274).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "get_inbox_urls", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the per-subscriber interest-map pattern (dual-cadence full-replace + incremental-extend with overlapping watermarks, domain-filtered explicit targets, zero-target short-circuit before spawning work). Adapt the polling intervals to your write volume and swap the trait-seamed data source for your own storage. Omit the ActivityPub inbox semantics if your dispatcher targets webhooks rather than federated inboxes.
