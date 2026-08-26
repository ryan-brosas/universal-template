<!-- capsule-v2 -->
# Capability-gated registration & roots sync — how do reference servers adapt their surface to what the client actually declared?

**Source:** modelcontextprotocol/servers MIT `main@76d64c8`; Codebase Memory `servers`. **Question:** When must a server withhold tools that need client capabilities, and how should client roots be fetched once and kept fresh?

## Register elicitation/sampling/roots tools only post-init; cache roots per session with a live re-fetch handler
**Path/Symbol:** `src/everything/tools/index.ts:registerConditionalTools` (:45–55 — get-roots-list, trigger-elicitation-request, trigger-url-elicitation, trigger-sampling-request, task-based research + async variants); gate check `src/everything/tools/trigger-elicitation-request.ts` (:39–47); roots sync `src/everything/server/roots.ts:syncRoots` (:31–90).

**Signature:** `syncRoots(server: McpServer, sessionId?: string): Promise<Root[] | undefined>`; `registerTriggerElicitationRequestTool(server: McpServer): void` (no-op when capability missing).

### Decisive source
```ts
// src/everything/server/roots.ts:32-36 + 76-85 — gate, then cache+subscribe
const clientCapabilities = server.server.getClientCapabilities() || {};
const clientSupportsRoots: boolean = clientCapabilities?.roots !== undefined;
if (clientSupportsRoots) {
  ...
  if (!roots.has(sessionId)) {
    // Set the list changed notification handler
    server.server.setNotificationHandler(
      RootsListChangedNotificationSchema,
      requestRoots          // re-fetches and refreshes the cache
    );
    await requestRoots();   // initial fetch immediately
  }
  return roots.get(sessionId);
}
```
The tool-level twin gate (`trigger-elicitation-request.ts:40–46`) reads the same capabilities object and simply does NOT call `server.registerTool` when `clientCapabilities.elicitation === undefined` — the tool never appears in `tools/list`.

**Flow:** factory registers unconditional tools → client initializes → `oninitialized` fires → `registerConditionalTools` reads now-known capabilities → eligible tools attach; ineligible ones silently never exist. Separately, `syncRoots` runs once per session (delayed 350ms so it doesn't race the initialized notification, see server-factory.md), stores roots in `Map<sessionId|undefined, Root[]>`, and installs a `notifications/roots/list_changed` handler whose callback re-requests and overwrites that session's entry — idempotent thereafter.

**Invariant:** a server MUST NOT send requests for capabilities the client never declared (spec MRTR rule mirrored here as registration gating) — the reference implementation enforces it by making the tool nonexistent rather than erroring at call time. And roots are cached PER SESSION KEY with `undefined` legal for stdio's single-session case; porters keying on a hardcoded session id break multi-client HTTP hosts.

**Probe:** `src/everything/__tests__/registrations.test.ts::"should register conditional tools based on capabilities"` (:48) vs `::"should not register conditional tools when capabilities missing"` (:87 — asserts zero registrations with empty capabilities); mock-server harness `tools.test.ts:createMockServer` (:19–42, `getClientCapabilities` stubbed to `{}`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "getClientCapabilities registerConditionalTools syncRoots list_changed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capability-read-at-registration gating (absent tool beats present-but-erroring tool), per-session roots caching, notification-driven re-fetch, and delayed first request after init; adapt which capabilities you gate on and your root-validation policy; omit async/task-based tool variants unless using the experimental tasks API.
