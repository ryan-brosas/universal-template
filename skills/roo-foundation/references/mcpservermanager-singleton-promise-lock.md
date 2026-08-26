<!-- capsule-v2 -->
# McpServerManager promise-lock singleton — how do you share ONE set of MCP server connections across multiple webview panels without double-connecting or racing initialization?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How is the hub singleton created so concurrent callers during startup all await the same initialization?

## Promise-slot lock with double-check inside
**Path/Symbol:** `src/services/mcp/McpServerManager.ts` (whole file, 86L: `getInstance` :20–54; provider registry :12/:60–62; broadcast :67–73; cleanup :78–85).
**Signature:** `static async getInstance(context: vscode.ExtensionContext, provider: ClineProvider): Promise<McpHub>`.
**Data Shape:** static fields: nullable `instance: McpHub | null`, `initializationPromise: Promise<McpHub> | null`, `providers: Set<ClineProvider>`; global-state key `"mcpHubInstanceId"` stamps the primary.

### Decisive source
```ts
// :30-53 — late joiners return the SAME in-flight promise; instance double-checked inside
if (this.initializationPromise) { return this.initializationPromise }
this.initializationPromise = (async () => {
    try {
        if (!this.instance) {
            const hub = new McpHub(provider)
            await hub.waitUntilReady()      // all servers connected OR individually timed out
            this.instance = hub
            await context.globalState.update(this.GLOBAL_STATE_KEY, Date.now().toString())
        }
        return this.instance
    } finally {
        this.initializationPromise = null   // cleared on success AND error so a failed init can retry
    }
})()
return this.initializationPromise
```

**Flow:** every caller registers its provider FIRST (:22 — even when the instance already exists, so broadcasts reach it) → existing instance returned immediately → else attach to or create THE initialization promise → hub constructed + `waitUntilReady()` awaited before publication → finally clears the slot.
**Invariant:** `waitUntilReady` gates PUBLICATION, not construction — servers connect/times-out per-server inside McpHub's own `initializationPromise` (:171–174/:181–183), so one dead server can never block singleton readiness forever; clearing the promise-slot in `finally` is what makes a failed first init retryable instead of caching a rejection.
**Probe:** describe-level coverage lives in the ClineProvider sticky-mode specs (`src/core/webview/__tests__/ClineProvider.sticky-mode.spec.ts`, parse_partial-flagged at pin); deterministic probe pins shape:
`grep -c 'this.initializationPromise' src/services/mcp/McpServerManager.ts` = **5** (:30 gate, :31 early-return, :34 assignment, :49 finally-clear, :53 return), `grep -c 'GLOBAL_STATE_KEY' src/services/mcp/McpServerManager.ts` = **3** (:11 def, :44 write, :82 clear).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "McpServerManager singleton getInstance", limit: 5 });
// CLI verified @ pin: rank#1 line-exact → Method src/services/mcp/McpServerManager.ts getInstance 20-54 (total: 8)
```

## Verdict
Adopt the promise-slot + waitUntilReady-before-publish pattern for any shared resource broker across panels/workspaces. Adapt the global-state stamp to your telemetry/leader-election needs. Omit nothing — dropping the finally-clear reintroduces poison-promise caching.
