<!-- capsule-v2 -->
# Subscriptions (subscribe-and-notify) — how do clients receive server-initiated change notifications without a GET stream or session?

**Source:** modelcontextprotocol/specification MIT `main@57ac4a2ec742e0cb7622d899b0f5d3bcf769fd69`; Codebase Memory `modelcontextprotocol`. **Question:** What is the open/acknowledge/deliver/close contract of `subscriptions/listen`, and how do notifications stay demultiplexable on a shared channel?

## Opt-in filter + acknowledged-first + subscriptionId demux
**Path/Symbol:** `docs/specification/2026-07-28/basic/patterns/subscriptions.mdx` (whole page, 166L: Opening a Stream :12–38, Notification Filter :40–50, Acknowledgment :52–81, Receiving Notifications :83–105, Multiple Concurrent Subscriptions :107–114, Cancellation :116–126, **Graceful Closure :128–166**); wire types `schema/draft/schema.ts` (`SubscriptionFilter` :1270–1288 — `toolsListChanged?`, `promptsListChanged?`, `resourcesListChanged?`, `resourceSubscriptions?: string[]`; `SubscriptionsListenRequest` :1314–1317; `SubscriptionsListenResultMetaObject._meta."io.modelcontextprotocol/subscriptionId"` REQUIRED :1326–1347; `SubscriptionsListenResult` :1349–1359; `SubscriptionsAcknowledgedNotification` :1398–1401). The draft page carries identical normative text (:128–134) — one edit upstream lands in both.

### Decisive source
```md
# subscriptions.mdx:14-16, 54-59 (the ordering gate)
The client sends a subscriptions/listen request with a notifications filter...
The server MUST NOT send notification types the client has not explicitly requested.

The server MUST send notifications/subscriptions/acknowledged as the first
message carrying the subscription's ID in _meta ... and MUST NOT send any
notification on the subscription before it. On stdio, where every subscription
shares one channel, this ordering is defined per subscription ID and not per
channel: messages belonging to other subscriptions MAY be interleaved before it.
```
The acknowledgment's `notifications` field reflects the SUBSET the server agreed to honor — unsupported types are omitted; clients SHOULD diff it against what they asked for (:60–81). The subscription id IS the JSON-RPC id of the listen request; every later notification on that stream carries it in `_meta["io.modelcontextprotocol/subscriptionId"]`, which is how stdio clients demux concurrent subscriptions sharing one channel (:107–114). Request-scoped notifications (progress, logging) never ride the listen stream — they flow only with their originating request.

**Lifecycle + Graceful Closure (:116–166):** ends when the client cancels (close SSE stream on HTTP / `notifications/cancelled` referencing the listen id on stdio), when the SERVER tears it down, or on transport death. Server-initiated graceful end = respond to the ORIGINAL listen request with a completion result before closing the stream:
```json
{ "jsonrpc": "2.0", "id": 1, "result": {
    "resultType": "complete",
    "_meta": { "io.modelcontextprotocol/subscriptionId": 1 } } }
```
Refined 2026-08 drift (4df2d6b→57ac4a2e): the prose now says the result "carries no method-specific data beyond the standard result fields and subscription metadata" (:129–137) instead of calling it an *empty* result — the wire example and `schema.ts` still pin the minimal body (`SubscriptionsListenResult` doc: "The result body is otherwise empty"; example payload `{resultType:"complete", _meta.subscriptionId}` under `schema/draft/examples/SubscriptionsListenResult/`). Its presence tells the client "clean close"; absence implies unexpected disconnect, which the client MAY treat as a reconnect trigger (:156–158). Stdio holds NO subscription state across reconnects: the client MUST re-send `subscriptions/listen` (:161–162). This one RPC replaces both `resources/subscribe` and the HTTP GET endpoint of earlier revisions.

**Invariant:** nothing unsolicited ever flows — no notification type outside the acknowledged filter, none before the ack. Porters who emit list-changed notifications without checking the filter leak events across tenants; porters who skip the ack leave clients unable to distinguish "subscribed, quiet" from "request swallowed".

**Probe:** no runtime tests in the spec repo; machine-checkable anchors: `SubscriptionsListenResult` requires `_meta.subscriptionId` at the type level (schema.ts :1349–1359) and the graceful-close example payload validates via `scripts/validate-examples.ts`. Coverage caveat recorded honestly. (For the SERVER-side reference implementation of per-resource updated notifications, see `resource-updated-subscribe-ack.md` — a different mechanism that this page's listen stream supersedes for list-changed traffic.)

## Get live surrounding code
**Retrieve:** (`query` BM25 now zero-hits this doc-shaped graph — noise-label filtering; use `name_pattern`):
```bash
codebase-memory-mcp cli search_graph --project modelcontextprotocol \
  --name-pattern 'SubscriptionsListenRequest|SubscriptionFilter|subscriptionId' --limit 10
```

## Verdict
Adopt explicit-filter opt-in streams, ack-first-per-subscription ordering, id-derived subscriptionId demux, the `resultType:"complete"` graceful-closure response (minimal body: standard fields + subscription metadata only), and re-subscribe-after-reconnect; adapt your event bus and filter storage to host; omit legacy resources/subscribe + GET-stream compatibility unless you deliberately serve ≤2025-11-25 revisions.
