<!-- capsule-v2 -->
# Shared-inbox receive gate — how do you accept signed inbound activities without deadlocking your own federation?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** What guards stand between an HTTP POST to /inbox and activity processing, and why is the whole receive wrapped in a 9-second timeout?

## shared_inbox + ReceivedActivity dedup
**Path/Symbol:** `crates/apub/apub/src/http/mod.rs:shared_inbox` (:44–60) with hook `Dummy: ReceiveActivityHook` (:62–85); route table `crates/apub/apub/src/http/routes.rs` (`/inbox` behind `InboxRequestGuard` :66–88); timeout const `INCOMING_ACTIVITY_TIMEOUT = 9 s` (:42) vs outbound `REQWEST_TIMEOUT = 10 s` (`crates/utils/src/lib.rs:22`).
**Signature:** `shared_inbox(request: HttpRequest, body: Bytes, data: Data<LemmyContext>) -> LemmyResult<HttpResponse>`; generic core `receive_activity_with_hook::<SharedInboxActivities, UserOrCommunity, LemmyContext>(request, body, hook, &data)`.
**Data Shape:** dispatch enum `SharedInboxActivities` (untagged, ordered — catch-all LAST, see announce capsule); hook runs AFTER signature verification but BEFORE verify/receive.

### Decisive source
```rust
// http/mod.rs:49-59 — the timeout is SHORTER than the sender's request timeout on purpose:
// a slow internal fetch would otherwise let OUR response hang until the PEER times out and
// marks us dead; better to fail this one activity fast and move the queue forward.
let receive_fut =
  receive_activity_with_hook::<SharedInboxActivities, UserOrCommunity, LemmyContext>(
    request, body, Dummy, &data);
timeout(INCOMING_ACTIVITY_TIMEOUT, receive_fut)
  .await
  .with_lemmy_type(UntranslatedError::InboxTimeout.into())?   // 9s < peer's 10s reqwest timeout

// http/mod.rs:71-84 — inside the hook: idempotency stamp + plugin surface
debug!("Received activity {}", activity.id().to_string());
ReceivedActivity::create(&mut context.pool(), &activity.id().clone().into()).await?;
plugin_hook_after("activity_after_receive", activity);

// routes.rs:78-87 — guard keeps webfinger/RSS GETs out of the inbox service (root-path scope)
if ctx.head().method != Method::POST { return false; }
ctx.head().headers.get(header::CONTENT_TYPE)?
  .as_bytes().starts_with(b"application/")
```

**Flow:** POST /inbox → guard filters method+content-type → library verifies HTTP signature and resolves the signing actor → `Dummy.hook` INSERTs the activity ap_id into `received_activity` (`on_conflict_do_nothing`; a true duplicate insert ERRORS the receive — dedup happens here, not in handlers) and fires the plugin hook → untagged-enum deserialize picks the activity type → per-type `verify()` then `receive()` run under the 9 s cap.
**Invariant:** inbound processing must finish faster than the SENDER's outbound timeout (9 s < 10 s) or healthy peers will mark you dead and back off — internal fetch latency is capped by construction, not hope. Every received activity id is stamped exactly once; duplicate delivery is rejected at the door. The inbox scope must not swallow non-AP traffic on shared paths.
**Probe:** `crates/db_schema/src/impls/activity.rs` test `receive_activity_duplicate` (:78–89, second create errors); fixture-level parse tests in `crates/apub/activities/src/activity_lists.rs:111–131`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "shared_inbox", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the receive-side contract: signature check → once-only idempotency stamp → typed verify/receive, all under an explicit deadline strictly shorter than peers' client timeouts, with route guarding so the endpoint doesn't cannibalize other traffic. Adapt timeouts to your transport and swap HTTP signatures for your auth scheme. Omit the actix/awc specifics.
