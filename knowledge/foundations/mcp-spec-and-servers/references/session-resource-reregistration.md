<!-- capsule-v2 -->
# Session-resource re-registration — how do tools create resources at runtime without tripping "already registered", and why return a ResourceLink?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821` (src/everything); Codebase Memory `servers`. **Question:** What is the idempotent register-or-replace ladder for session-scoped resources created by tools?

## Map-tracked remove-then-register keyed by URI
**Path/Symbol:** `src/everything/resources/session.ts` (whole file, 80L: tracking map :9; URI scheme :17–19; `registerSessionResource` :32–80). SDK types: `RegisteredResource.remove()`, return type `ResourceLink`.

**Signature:** `registerSessionResource(server, resource, "text"|"blob", payload) → ResourceLink`. Module-level `const registeredResources = new Map<string, RegisteredResource>()` keys the LIVE registration handle by resource URI. URI scheme `demo://resource/session/<name>` (:17–19).

### Decisive source
```ts
// src/everything/resources/session.ts (condensed decisive sequence)
// Check if a resource with this URI is already registered and remove it
const existingResource = registeredResources.get(uri);
if (existingResource) {
  existingResource.remove();          // dispose previous registration handle
  registeredResources.delete(uri);
}

// Register file resource
const registeredResource = server.registerResource(
  name, uri,
  { mimeType, description, title, annotations, icons, _meta },   // metadata passthrough
  async () => ({ contents: [resourceContent] })   // payload CAPTURED at write time
);

registeredResources.set(uri, registeredResource);  // track for next re-registration
return { type: "resource_link", ...resource };     // tool result advertises the new resource
```

**Flow:** a tool generates an artifact → calls `registerSessionResource` with full Resource metadata + text/blob payload → module map checked: existing handle for this URI ⇒ `.remove()` first (the in-file comment :5–8 names the failure being prevented: `"Resource already registered"` errors when a tool creates the same URI repeatedly during a session) → fresh `server.registerResource` whose read handler returns the CAPTURED payload (closure over `resourceContent`, not re-read from anywhere) → handle stored → tool returns `{ type: "resource_link", ...resource }` so the client sees a clickable reference instead of inline content.

**Invariant:** same-URI re-registration MUST go through remove-then-register — calling `server.registerResource` twice on one URI throws and aborts the tool call. The read closure returns the payload captured AT REGISTRATION TIME: later calls to `registerSessionResource` with the same URI replace content precisely because the old handle was disposed. The returned `resource_link` block is the contract that lets a tool hand the client a stable pointer (client then `resources/read`s it) rather than duplicating bytes into the tool result. Session scope = lifetime of the server instance here; there is no TTL sweep (coverage caveat for long-lived hosts).

**Probe:** `src/everything/__tests__/resources.test.ts:186–265` — mock-server pins the exact `registerResource(name, uri, objectContaining({mimeType, description}), fn)` call shape (:213–221); returned link asserts `type === 'resource_link'` with uri/name passthrough (:209–211); the captured read handler resolves `contents[0].text` to the registered payload (:242–264). URI scheme pinned at :174–184.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "registerSessionResource RegisteredResource remove resource_link", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the map-keyed remove-then-register ladder for any tool-created runtime resource, payload-capturing closures, and resource_link returns from creating tools; adapt the tracking-map scope to your host's session model (per-session maps for multi-session hosts); omit direct double-registration (throws) and inline-content duplication of large artifacts.
