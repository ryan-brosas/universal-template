<!-- capsule-v2 -->
# dsh-mem0 plugin mount — how does a harness register auto-revertible memory tools?

**Source:** mem0 Apache-2.0 `main@7e09615`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** How does a plugin hand two agent-callable tools to a host tool registry such that they unmount cleanly, and what must be validated before any client is constructed?

## Plugin entry contract
**Path/Symbol:** `integrations/dsh-mem0/src/index.ts` (`apply`, lines 69-138; module exports lines 20-21).
**Signature:** `export function apply(ctx: Context, config: Config): void`.
**Data Shape:** `Config = { apiKey?: string; userId: string; host?: string }`. `apiKey` falls back to `process.env.MEM0_API_KEY`; `userId` is REQUIRED (no env fallback); `host` optionally spreads into the `MemoryClient` constructor only when truthy (`...(config.host ? { host: config.host } : {})`). Module also exports `name = "mem0"` and `inject = ["tools"]`.

### Decisive source
```ts
const apiKey = config.apiKey ?? process.env.MEM0_API_KEY;
if (!apiKey) {
  throw new Error("dsh-mem0: set config.apiKey or the MEM0_API_KEY env var");
}
const userId = config.userId;
if (!userId) {
  throw new Error("dsh-mem0: config.userId is required");
}
const client = new MemoryClient({ apiKey, ...(config.host ? { host: config.host } : {}) });
ctx.tools.register(defineTool({ name: "search_memory", ... }));
ctx.tools.register(defineTool({ name: "add_memory", ... }));
```

**Flow:** validate apiKey → validate userId → construct one shared `MemoryClient` → register `search_memory` → register `add_memory`. Both tools close over the single client; no per-call construction.
**Invariant:** Validation happens INSIDE `apply` BEFORE any registration or client construction — a misconfigured plugin must throw at mount time (Cordis surfaces it as a failed plugin load), never lazily on first tool call. `inject = ["tools"]` is load-bearing: Cordis defers the whole module until a `tools` service exists, so `ctx.tools` is always present inside `apply`. Registrations are Cordis revertible effects — unregistering is automatic on plugin unmount; never store registrations in module scope.
**Probe:** `integrations/dsh-mem0/tests/apply.test.ts` ("throws when no apiKey…", "throws when userId is missing", "registers both memory tools" asserting sorted keys `["add_memory","search_memory"]`) — real suite runs offline via `cd integrations/dsh-mem0 && vitest run` (peer deps are mocked).
**Retrieve:** search_graph project `mnt-hdd-utopia-inspo-memory-mem0` query `dsh mem0 plugin apply` limit 3 → `integrations.dsh-mem0.src.apply` Function index.ts 69-138.

## Verdict
Adopt the mount-time validation ladder (apiKey→env fallback, required userId, fail fast before side effects), the `inject`-gated module shape, and closure over ONE shared client. Adapt `Context`/`defineTool` to your host's DI/tool API. Omit nothing — the file is the whole contract.
