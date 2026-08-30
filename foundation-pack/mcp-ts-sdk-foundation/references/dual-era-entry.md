<!-- capsule-v2 -->
# Dual-era HTTP entry — how does one fetch-style handler route legacy vs modern traffic, construct per-request instances, and own the subscriptions bus?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What is the composition order for an entry that serves both protocol eras, pre-dispatch gates, per-request factories, and change-event fan-out?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/createMcpHandler.ts`: `createMcpHandler` (:622-933), `serveModern` (:668-831), `handle` (:855-907); wiring of `InMemoryServerEventBus`/`createServerNotifier`/`createListenRouter` (:647-656). NEW at this pin: `standardHeadersOf` shared header reader (:421-427) feeding BOTH the classifier and `validateStandardRequestHeaders` (see version-header-presence-gate.md — the missing-header rejection cell lives there).
**Signature:** `createMcpHandler(factory: McpServerFactory, options?): McpHttpHandler { fetch(request, requestOptions?), notify: ServerNotifier, bus, close() }`.
**Data Shape:** `legacy: 'stateless' | 'reject'` posture (default stateless; construction-time TypeError if a JS caller passes a handler function — loud beats silently treating it as the default). In-flight modern instances tracked in a Set so `close()` tears them down.

### Decisive source
```ts
// Content-Type check answered BEFORE the body is read … Load-bearing for the
// modern leg, whose ladder does not inspect Content-Type.
if (request.method.toUpperCase() === 'POST' && !isJsonContentType(…)) return jsonRpcErrorResponse(415, -32_000, …);
const classified = await classifyEntryRequest(request, requestOptions?.parsedBody);
switch (outcome.kind) {
  case 'modern': return await serveModern(outcome, request, authInfo);
  case 'legacy': return await serveLegacyRoute(outcome, forwardRequest, authInfo, parsedBody);
}
```
serveModern order: supported-revision gate (−3222 naming endpoint's list) → SEP-2243 standard-header rung → pre-dispatch client-capability gate (pins spec's unconditional 400 BEFORE factory construction) → factory({era:'modern',authInfo,request}) → subscriptions/listen short-circuit (factory constructed ONLY to read declared capabilities; instance never connected) → tools/call `Mcp-Param-*` validation against the instance's registry → era-write + modern-only handler install → invoke via per-request transport.

**Flow:** notification exchanges have no terminal response to ride auto-close ⇒ released explicitly via queueMicrotask after invoke. ConnectionClosed mid-exchange answers 499. Factory failure closes the instance AND removes it from inflight so repeated failures cannot accumulate connected instances.

**Invariant:** The capability gate runs at the ENTRY (pre-factory) so the spec-mandated 400 holds even though dispatch would also produce −32021 — and the transport maps post-window −32021 identically, making the status origin-independent. Legacy-classified NOTIFICATIONS on a modern-only endpoint are acknowledged-and-dropped (202, never dispatched). Token verification belongs in middleware mounted IN FRONT of this entry, not in the factory.

**Probe:** `packages/server/test/server/createMcpHandlerListen.test.ts` :86 ("serves listen at the entry, consulting the factory only for its declared capabilities"), :228 ("handler.close() emits the empty subscriptions/listen result … graceful-close signal"); dual-era matrix `test/integration/test/client/versionNegotiation.test.ts`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "createMcpHandler serveModern legacyStatelessFallback", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt classify→gate→factory→invoke ordering with entry-owned capability pinning; adapt posture options to your compat needs; omit the listen-router ownership if you don't expose subscriptions.
