<!-- capsule-v2 -->
# Capability-declared handler pre-install — how does a server answer `tools/list` with zero registrations without "Method not found"?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Handlers install lazily on first registration — how do you satisfy the spec rule that a declared capability MUST answer its list method even when nothing is registered yet?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/mcp.ts`: constructor (:117-134), `setToolRequestHandlers` (:161-239), `assertCanSetRequestHandler` guards (:166-167), `_toolHandlersInitialized`/`_resourceHandlersInitialized`/`_promptHandlersInitialized`/`_completionHandlerInitialized` latches (:159, :336, :423, :518).
**Signature:** `constructor(serverInfo, options?)` → per-capability eager `set*RequestHandlers()`; every installer re-checks its boolean latch.
**Data Shape:** Insertion-ordered plain-object registries: `_registeredTools/_registeredPrompts` keyed by name, `_registeredResources` by uri, `_registeredResourceTemplates` by name.

### Decisive source
```ts
if (options?.capabilities?.tools)     this.setToolRequestHandlers();
if (options?.capabilities?.resources) this.setResourceRequestHandlers();
if (options?.capabilities?.prompts)   this.setPromptRequestHandlers();

private setToolRequestHandlers() {
    if (this._toolHandlersInitialized) return;
    this.server.assertCanSetRequestHandler('tools/list');   // throws if already connected
    this.server.assertCanSetRequestHandler('tools/call');
    this.server.registerCapabilities({ tools: { listChanged: this.server.getCapabilities().tools?.listChanged ?? true } });
    // tools are listed in registration (insertion) order — deterministic across requests
```

**Flow:** declare capability up front → handlers installed EAGERLY at construction (list methods answer `{tools:[…]}` etc.) → first `registerTool/Resource/Prompt` calls the same installer (latch makes it a no-op) → each registration appends to the insertion-ordered registry and fires the matching list-changed notification (only when connected). Low-level `Server` users get no such courtesy — the ServerOptions docblock states they own every declared handler.

**Invariant:** `assertCanSetRequestHandler` before install = fail-fast on post-connect mutation (mirrors `registerCapabilities` throwing after transport connect). The `listChanged` advertised bit defaults TRUE when the user didn't set it — registration then emits real change notifications. Ordering guarantee comes free from JS object insertion order; do not sort.

**Probe:** `packages/server/test/server/listOrdering.test.ts` (insertion-order listing); `test/integration/test/server/mcp.test.ts` :1247/:2609/:2669/:3608 ("already registered" duplicates throw); `mcp.compat.test.ts` (empty-registry list answers).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "McpServer constructor setToolRequestHandlers assertCanSetRequestHandler registerCapabilities", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt eager-install-on-declared-capability + one-way latches + insertion-order registries for any registry-backed RPC surface; adapt method names; omit MCP-specific result shapes.
