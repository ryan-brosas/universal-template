<!-- capsule-v2 -->
# Tool-list config merge (alwaysAllow/disabledTools + wildcard) — how do you stamp per-tool policy flags onto a server's live tool list by re-reading the config FILE, not the in-memory copy?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Where do `alwaysAllow` / `disabledTools` / the `"*"` wildcard get applied to fetched tools, and why does that path re-read JSON from disk?

## fetchToolsList merges disk config into SDK tool descriptors
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`fetchToolsList` :980–1038; wildcard check :1023–1024; stamping map :1027–1031; consumers `toggleToolAlwaysAllow` :1862–1877 and `toggleToolEnabledForPrompt` :1879–1894 via `updateServerToolList` :1780–1860).
**Signature:** `private async fetchToolsList(serverName: string, source?: "global" | "project"): Promise<McpTool[]>`.
**Data Shape:** emits SDK tool objects EXTENDED with two hub-owned flags: `alwaysAllow: boolean` (`hasWildcard || alwaysAllowConfig.includes(tool.name)`), `enabledForPrompt: boolean` (`!disabledToolsList.includes(tool.name)`). Config lists read from the source-appropriate file: project `.roo/mcp.json` or global settings; defaults `[]` on any read failure ("Continue with empty configs" :1020).

### Decisive source
```ts
// :1023-1031
const hasWildcard = alwaysAllowConfig.includes("*")
const tools = (response?.tools || []).map((tool) => ({
    ...tool,
    alwaysAllow: hasWildcard || alwaysAllowConfig.includes(tool.name),
    enabledForPrompt: !disabledToolsList.includes(tool.name),
}))
```
```ts
// :1886-1889 — inverted polarity at the toggle boundary
// When isEnabled is true, we want to remove the tool from the disabledTools list.
const addToolToDisabledList = !isEnabled
```

**Flow:** `tools/list` request over connection → RE-READ raw mcp.json for this server's `alwaysAllow`/`disabledTools` (:997–1017) → stamp flags per tool. UI toggles go through `updateServerToolList`, which edits the parsed file object idempotently (push only if absent / splice only if present), writes via safeWriteJson under the echo-suppression latch, then REFRESHES the list through `fetchToolsList` so the connection reflects disk.
**Invariant:** policy lives on DISK as the single source of truth — the in-memory `server.config` string is stale-prone, so flag refreshes always round-trip the file; `"*"` means all-current-tools allowed but is evaluated at fetch time, so tools added later inherit it automatically.
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts`: it `"should mark all tools as always allowed when wildcard is present"` (:915–962), it `"should support both wildcard and specific tool names in alwaysAllow"` (:963–1008), it `"should initialize alwaysAllow if it does not exist"` (:869–914); mirror trio for disabledTools at :1057/:1105/:1153.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "fetchToolsList alwaysAllow wildcard disabledTools", limit: 5 });
// CLI verified @ pin: rank#1 line-exact → McpHub.fetchToolsList Method src/services/mcp/McpHub.ts 980-1038 (total: 1)
```

## Verdict
Adopt disk-as-truth flag stamping with wildcard-at-fetch semantics. Adapt flag names to your prompt builder's vocabulary. Omit the VSCode-specific notification fan-out after toggles.
