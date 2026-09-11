<!-- capsule-v2 -->
# Resource-subscription acknowledge plane — how does a server wire resources/subscribe so clients get notifications/resources/updated ONLY for URIs they explicitly subscribed to?

**Source:** modelcontextprotocol/servers MIT `main@599dafc1054550a6eeb87a6545c1e1b03b3ca827`; Codebase Memory `servers`. **Question:** What is the minimal correct registration shape for `resources/subscribe` + `notifications/resources/updated`, and what do its request handlers return?

## Memory-server subscription trio (capability → handlers → gated notify)
**Path/Symbol:** `src/memory/index.ts` — `registerKnowledgeGraphSubscriptions` :576–589 (whole export); module-level `resourceSubscribers` Set :264–266; `notifyGraphUpdated` gate :268–274; six mutation-tool call sites :297/:326/:361/:391/:424/:454; main() wiring :592.
**Signature:** `export function registerKnowledgeGraphSubscriptions(server: McpServer): void` — reaches the low-level SDK via `server.server.registerCapabilities(...)` / `server.server.setRequestHandler(...)` / `server.server.sendResourceUpdated(...)`, bypassing McpServer sugar because `resources/subscribe` has none.
**Data Shape:** `resourceSubscribers = new Set<string>()` of RAW subscribed URI strings (this server hosts exactly one resource, `memory://knowledge-graph`; one stdio session per process ⇒ no session dimension — contrast everything-server's `Map<uri, Map<sessionId, interval>>`). Handlers receive `{ params: { uri } }` and return the empty object; the notification carries `{ uri }` only.

### Decisive source
```ts
// src/memory/index.ts:576-589 (verbatim)
export function registerKnowledgeGraphSubscriptions(server: McpServer) {
  server.server.registerCapabilities({ resources: { subscribe: true } });
  server.server.setRequestHandler(SubscribeRequestSchema, async (request) => {
    resourceSubscribers.add(request.params.uri);
    return {};
  });
  server.server.setRequestHandler(UnsubscribeRequestSchema, async (request) => {
    resourceSubscribers.delete(request.params.uri);
    return {};
  });
}
// ...and the emit-side gate (:268-274):
function notifyGraphUpdated() {
  if (resourceSubscribers.has(RESOURCE_URI)) {
    server.server.sendResourceUpdated({ uri: RESOURCE_URI });
  }
}
```

**Flow:** register capability + both handlers at startup (:592) → client sends `resources/subscribe {uri}` → URI added to the Set → handler resolves `{}` (the JSON-RPC RESULT — an acknowledgment, not data) → every mutating tool (`create_entities`, `delete_entities`, all observation/relation writers) ends by calling `notifyGraphUpdated()` → the gate emits `notifications/resources/updated {uri}` only when the URI is still subscribed → `resources/unsubscribe` deletes the URI → subsequent mutations become silent no-ops.
**Invariant:** THREE load-bearing rules a porter breaks silently: (1) **subscribe/unsubscribe handlers MUST resolve an empty result** — they are acknowledgments; returning anything else (or throwing on unknown URIs, which delete tolerates) violates the protocol shape. (2) **The gate lives on the EMIT side, not the receive side** — every mutation path calls `notifyGraphUpdated()` unconditionally; membership is checked at emission so an unsubscribed client's mutations stay cheap and quiet. Forgetting the `.has()` check spams unsubscribed clients (spec violation); forgetting the unconditional call sites leaves subscribers stale. (3) The `subscribe: true` capability must be declared or well-behaved clients will never send the requests at all.
**Probe:** `src/memory/__tests__/resource.test.ts` (97L, real vitest suite) pins ALL of it: `declares the resources.subscribe capability` :68–76 asserts `registerCapabilities({ resources: { subscribe: true } })`; `registers subscribe and unsubscribe request handlers` :78–86 asserts both schemas got handlers; `subscribe and unsubscribe handlers acknowledge with an empty result` :88–96 asserts BOTH resolve `{}`; companion describe block :10–49 pins resource registration metadata (kebab name `knowledge-graph`, `memory://knowledge-graph`, `application/json`) and the read-handler JSON round-trip with `readGraph` called once.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", name_pattern: "registerKnowledgeGraphSubscriptions|SubscribeRequestSchema|UnsubscribeRequestSchema", limit: 10, fields: ["signature", "name", "file"] });
```
(Live-executed at `599dafc1`: name-pattern resolves `servers.src.memory.registerKnowledgeGraphSubscriptions` Function src/memory/index.ts :576–586; the broad semantic-query form returns weak cross-server noise — use the pinned pattern.)

## Verdict
Adopt the trio shape — declare `resources.subscribe`, register raw-schema handlers resolving `{}`, gate every change notification behind subscriber-set membership checked AT EMISSION — and the unconditional-notify-at-every-mutation-site discipline that makes the gate correct; adapt storage of the subscriber set to your session topology (add the session dimension if you serve HTTP multi-session, as everything-server's fanout map does); omit McpServer-sugar expectations (none exists for subscribe) and don't conflate these `{}` acks with the `subscriptions/listen` graceful-closure completion result (that one signals teardown and IS documented in `subscriptions.md`). Direct-test coverage complete at `599dafc1`.
