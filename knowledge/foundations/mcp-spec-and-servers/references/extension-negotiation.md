<!-- capsule-v2 -->
# Extension negotiation (SEP-2133, Final) — how do clients and servers advertise and gate optional protocol extensions?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6` (`seps/2133-extensions.md`; normative text in `docs/specification/2026-07-28/basic/versioning.mdx` §Extension Negotiation :80–125). Codebase Memory `modelcontextprotocol`. **Question:** Beyond the core protocol, how are optional extensions identified, advertised in capabilities, and gated so a missing extension degrades gracefully instead of breaking?

## `{vendor-prefix}/{name}` identifiers advertised in an `extensions` capabilities map, with mandatory graceful degradation
**Path/Symbol:** `seps/2133-extensions.md` (whole SEP: definition + identifier grammar :22–34, official/experimental governance :36–64, lifecycle :66–115, negotiation :113–190); `docs/specification/2026-07-28/basic/versioning.mdx` §Extension Negotiation :80–125 (normative).

**Signature:** `capabilities.extensions?: { [extensionId: string]: JSONObject }` on both `ClientCapabilities` and `ServerCapabilities` (schema.ts, already pinned in `capability-negotiation-matrix.md`). Each extension defines the schema of its settings object; an empty object `{}` means "supported, no settings".

**Data Shape:** extension identifier = `{vendor-prefix}/{extension-name}` (e.g. `io.modelcontextprotocol/tasks`, `io.modelcontextprotocol/ui`, `com.example/websocket-transport`). The prefix is **mandatory**; names follow `_meta` key rules. Vendor prefix SHOULD be a reversed domain name the author owns (Java-package convention). Breaking changes MUST use a NEW identifier (`io.modelcontextprotocol/oauth-client-credentials-v2`).

### Decisive source
```json
// 2026-07-28/basic/versioning.mdx :90-104 (client advertising the Apps extension)
{
  "capabilities": {
    "roots": {},
    "extensions": {
      "io.modelcontextprotocol/ui": { "mimeTypes": ["text/html;profile=mcp-app"] }
    }
  }
}
// Tasks extension: "extensions": { "io.modelcontextprotocol/tasks": {} }
```

**Flow:** each party advertises the extensions it supports in the `extensions` map of its capabilities (client in the request, server in its capability response) → a party that wants to use an extension checks the OTHER side's map before offering extension-specific features → if the other side doesn't support it, the supporting party **MUST** either revert to core-protocol behavior or reject with an appropriate error if the extension is mandatory. Extensions SHOULD document their expected fallback.

**Invariant:** **graceful degradation is mandatory, not optional.** "If one party supports an extension but the other does not, the supporting party MUST either revert to core protocol behavior or reject the request with an appropriate error if the extension is mandatory." (versioning.mdx :121–125). A server offering UI-enhanced tools must still return meaningful text content to clients that don't support the UI extension; a server requiring a specific auth extension MAY reject connections from clients that don't support it. Server-side capability checking is presence-based (SEP-2133 :172–186): `clientCapabilities?.extensions?.["io.modelcontextprotocol/ui"]?.mimeTypes?.includes(...)` before registering UI tools, else register a text-only fallback. SDKs MUST implement extensions disabled-by-default with explicit opt-in. Treat all extension-provided fields as untrusted and validate them.

**Probe:** no runtime test in the spec repo (docs+SEP only — coverage caveat). Deterministic: the Tasks extension (`io.modelcontextprotocol/tasks`) is the flagship example — its capability gating is exercised by `servers/src/everything` task tools (see `task-based-tool-authoring.md` / `bidirectional-task-client.md`), and the schema types `extensions?: {[key]: JSONObject}` are machine-checkable in `capability-negotiation-matrix.md`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "extensions capability negotiation io.modelcontextprotocol/tasks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `{vendor-prefix}/{name}` extension identifier grammar (mandatory prefix, new-id for breaking changes) and advertise support in an `extensions` capabilities map with per-extension settings; gate extension-specific features on the peer's map with mandatory graceful degradation (fallback to core behavior, or reject if mandatory); adapt your vendor prefix and settings schema to your domain; omit treating extensions as core-protocol additions — they evolve and version independently. Complements `capability-negotiation-matrix.md` (pins the `extensions` map shape) and `tasks-extension-lifecycle.md` (the flagship extension instance).
