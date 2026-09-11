<!-- capsule-v2 -->
# Tool capability override keys — why does an Inspector disable survive tool re-registration?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** How do you disable a registered frontend tool at runtime WITHOUT the per-tool `available` flag being clobbered when a hook re-registers the tool?

## NUL-keyed override set independent of the tool objects
**Path/Symbol:** `packages/core/src/core/run-handler.ts:RunHandler.capabilityKey` (:1209-1211), `setToolEnabled`/`isToolEnabled` (:1219-1231), filter in `buildFrontendTools` (:1236-1250); store `_disabledToolKeys` (:136).
**Signature:** `capabilityKey(name: string, agentId?: string): string` → `` `${agentId ?? ""}\u0000${name}` ``; `setToolEnabled(name, enabled, agentId?): void`.
**Data Shape:** `Set<string>` of NUL-separated `agentId\u0000toolName` keys; absent = enabled (default-true semantics).

### Decisive source
```typescript
/** Stable identity for a tool override: agent-scope + name (NUL-separated). */
private capabilityKey(name: string, agentId?: string): string {
  return `${agentId ?? ""}\u0000${name}`;
}

buildFrontendTools(agentId?: string): Tool[] {
  return this._tools
    .filter(
      (tool) =>
        tool.available !== false &&
        (tool.available as boolean | string | undefined) !== "disabled" &&
        (!tool.agentId || tool.agentId === agentId) &&
        this.isToolEnabled(tool.name, tool.agentId),
    )
    .map((tool) => ({
      name: tool.name,
      description: tool.description ?? "",
      parameters: createToolSchema(tool),
    }));
}
```

**Flow:** Inspector calls `setToolEnabled(name, false, agentId?)` → key added to the set → `buildFrontendTools` intersects FOUR gates: not `available:false`, not `"disabled"` (legacy string form), agent-scope match (`!tool.agentId || tool.agentId === agentId`), and not override-disabled → because overrides live OUTSIDE the tool objects, a hook re-registering the same name+agentId (which resets its own `available`) cannot clobber the runtime disable. Catalog components use the identical pattern with `_disabledCatalogComponents` keyed by bare name (:128, :302-322).
**Invariant:** Override identity is `(agentId ?? "", name)` — NUL separator prevents `("ab","c")` colliding with `("a","bc")`. A disabled tool is omitted from what the agent receives at all; it never reaches the model as a callable.
**Probe:** `packages/core/src/core/__tests__/run-handler-capability-toggle.test.ts` :11 ("omits a tool from buildFrontendTools once disabled via setToolEnabled"), :36 (re-enable), :51 (per-agent scoping). Deterministic anchor `grep -c "setToolEnabled" packages/core/src/core/__tests__/run-handler-capability-toggle.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "capabilityKey setToolEnabled buildFrontendTools disabledToolKeys", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt external override sets for any capability toggled by an external UI while app code owns registration. Adapt key shape to your id space (keep the separator). Omit per-object flags as the sole mechanism — they are re-registration-volatile by construction.
