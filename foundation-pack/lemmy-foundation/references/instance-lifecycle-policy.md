<!-- capsule-v2 -->
# Instance lifecycle & federation policy — when does a peer queue exist, and who decides allowed vs blocked vs dead?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** What is the state machine of a remote instance row, and how do allowlist/blocklist and deadness interact to start/stop per-peer workers?

## Instance actions + SendManager gating
**Path/Symbol:** `crates/db_schema/src/source/instance.rs` (`InstanceActions::check_ban` / `check_application_allowed`, `read_federated_with_blocked_and_dead`); worker creation gate `crates/apub/send/src/lib.rs:do_loop` (:112–159); liveness writer `crates/apub/send/src/worker.rs:mark_instance_alive` (:295–313); ban checks consumed by activity senders (`crates/apub/activities/src/lib.rs:verify_person` :66–73).
**Signature:** `InstanceActions::check_ban(pool, person_id, instance_id)`; `Instance::update(pool, id, InstanceForm { updated_at, .. })`; query triple `(instance, allowed, is_dead) = read_federated_with_blocked_and_dead(pool)`.
**Data Shape:** `instance { domain (unique actor host), published_at, updated_at: Option<DateTime> (NULL ⇒ never seen alive), ... }`; policy rows in `federation_allowlist` / `federation_blocklist` keyed by instance_id; "dead" derived from staleness of `updated_at`.

### Decisive source
```rust
// worker.rs:295-312 — every real (non-skipped) send success refreshes peer liveness,
// but at most once per day per peer to keep write volume bounded:
let updated = self.instance.updated_at.unwrap_or(self.instance.published_at);
if updated.add(Days::new(1)) < Utc::now() {
  self.instance.updated_at = Some(Utc::now());
  Instance::update(&mut self.pool(), self.instance.id,
    InstanceForm { updated_at: Some(Utc::now()), .. }).await?;
}

// send/src/lib.rs:122-128 — the three-policy intersection decides worker existence
let should_federate = allowed && !is_dead;

// activities/src/lib.rs:66-73 — instance-level bans are enforced on EVERY inbound person use
async fn verify_person(person_id: &ObjectId<ApubPerson>, context) -> LemmyResult<()> {
  let person = person_id.dereference(context).await?;
  InstanceActions::check_ban(&mut context.pool(), person.id, person.instance_id).await?;
  Ok(())
}
```

**Flow:** an instance row appears when any AP object from that host is fetched → each reconcile tick evaluates allow ∧ ¬block ∧ ¬dead; passing peers get a queue worker, newly-blocked/dead peers lose theirs (worker cancel persists final queue state) → successful deliveries feed back `updated_at` (≤1 write/day/peer) which IS the liveness signal later used for deadness → instance-level bans short-circuit all per-activity person verifications.
**Invariant:** liveness is a BYPRODUCT of successful federation traffic, not a heartbeat — instances with no mutual activity age out via `updated_at` staleness, and the daily write throttle means the column approximates "last healthy exchange" not "last packet". Allow/block policy changes take effect within one reconcile interval without restarts.
**Probe:** `crates/apub/send/src/lib.rs` tests `test_send_manager_dead` (:362–380, zeroed `updated_at` excludes the peer), `test_send_manager_blocked` / `test_send_manager_allowed` (:319–357); `test_update_instance` (`crates/apub/send/src/worker.rs:670–683`) pins the success-refresh write.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "check_ban", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt peer-liveness-as-side-effect (throttled timestamp refresh on successful delivery), policy-intersection gating of per-peer workers with live add/remove, and host-level bans checked once at person-verification instead of per-object. Adapt staleness thresholds and the allow/block model (e.g. to webhook endpoint health) to your ops surface. Omit Lemmy's content-level slur/filter machinery — separate plane.
