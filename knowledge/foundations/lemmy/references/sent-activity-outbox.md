<!-- capsule-v2 -->
# SentActivity outbox table + ActivityChannel — how does a web request hand off federation work in O(1) without losing it?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** What exactly is written at API time so the send workers can run later, and why is there an unbounded channel in front of the DB?

## SentActivity / SentActivityForm / ActivitySendTargets
**Path/Symbol:** `crates/db_schema/src/source/activity.rs:ActivitySendTargets` (:15–54), `SentActivity` (:60–71), `SentActivityForm` (:75–84), `ReceivedActivity` (:91–94); writer `crates/apub/activities/src/lib.rs:send_lemmy_activity` (:105–135); channel `crates/api/api_utils/src/send_activity.rs:ActivityChannel` (:128–164); dispatcher `match_outgoing_activities` (`crates/apub/activities/src/lib.rs:145–394`, ~30-variant enum match).
**Signature:** `SentActivity::create(pool, form)` (impls :15–23); `ActivityChannel::submit_activity(data, &ctx) -> LemmyResult<()>`; `retrieve_activity() -> Option<SendActivityData>`.
**Data Shape:** row = `{ id (serial = global delivery order), ap_id, data: serde_json::Value (the raw activity JSON), sensitive: bool (GET gate), published_at, send_inboxes: Vec<Option<DbUrl>>, send_community_followers_of: Option<CommunityId>, send_all_instances: bool, actor_type: ActorType, actor_apub_id }`. Targets are a THREE-WAY union, resolved later per receiving instance.

### Decisive source
```rust
// api_utils/send_activity.rs:150-157 — fire-and-forget enqueue: if no consumer task is running
// (weak sender expired), the send is SILENTLY DROPPED rather than blocking or erroring
if let Some(sender) = ACTIVITY_CHANNEL.weak_sender.upgrade() {
  sender.send(data)?;
}
Ok(())

// apub/activities/src/lib.rs:118-132 — the ONLY durable write happens on the consumer side:
// serialize activity → SentActivityForm → INSERT. Serial id becomes the delivery order.
let form = SentActivityForm {
  ap_id: activity.id().clone().into(),
  data: serde_json::to_value(activity)?,
  sensitive,
  send_inboxes: send_targets.inboxes.into_iter().map(Some).collect(),
  send_all_instances: send_targets.all_instances,
  send_community_followers_of: send_targets.community_followers_of.map(|e| e.0),
  actor_type: actor.actor_type(),
  actor_apub_id: actor.id().clone().into(),
};
SentActivity::create(&mut data.pool(), form).await?;
```

**Flow:** API handler builds a typed `SendActivityData` variant → `submit_activity` pushes onto the process-global unbounded channel (weak sender: zero cost when federation disabled) → the dedicated `handle_outgoing_activities` task drains it forever (`retrieve_activity` loop :137–143), matches the variant to an activity constructor, and INSERTs one `sent_activity` row → instance workers poll the table by serial id. Receive-side twin: `ReceivedActivity::create` uses `on_conflict_do_nothing` and treats "0 rows affected" as a duplicate error (`crates/db_schema/src/impls/activity.rs:46–62`).
**Invariant:** request latency never depends on network sends; durability begins at the channel consumer's INSERT, and from then on ordering = serial id (the contract every worker cursor relies on). The three target kinds must be preserved verbatim through serialization because different receivers claim an activity under different clauses.
**Probe:** `crates/db_schema/src/impls/activity.rs` tests `sent_activity_write_read` (:93–122, insert→read-back round-trip) and `receive_activity_duplicate` (:78–89, second identical receive errors).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "SentActivity", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the transactional-outbox shape (typed intent → single durable row carrying routing metadata + payload + monotone id) with an in-process queue only as a latency shield, plus the weak-sender kill switch making federation optional at runtime. Adapt column set and the channel policy (Lemmy accepts drop-on-no-consumer; stricter hosts should fail loud). Omit the concrete SendActivityData variant list — it is product surface.
