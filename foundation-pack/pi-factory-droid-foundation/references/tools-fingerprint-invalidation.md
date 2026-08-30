<!-- capsule-v2 -->
# Stable tools fingerprint → pool invalidation — how do I detect "the tool set changed" cheaply and rebuild only what depends on it?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** A long-lived pooled agent session captured my tool set at creation time — how do I notice a mid-conversation tool change and rebuild exactly the dependent artifacts?

## Order-normalized sha256 over name+description+parameters
**Path/Symbol:** `src/pi-tools-bridge.ts:fingerprintTools` (29-37); consumed at `src/pi-tools-mode.ts:toolsFingerprintOf` (289-291) and `src/providers.ts:getOrCreateEntry` (660-663).
**Signature:** `fingerprintTools(tools: Tool[] | undefined): string` — sha256 hex of a JSON array sorted by `name.localeCompare`.
**Data Shape:** Fingerprint input per tool: `{name, description: t.description ?? "", parameters: t.parameters ?? {}}` — missing fields normalize to empty so the same logical set always hashes identically.

### Decisive source
```ts
export function fingerprintTools(tools: Tool[] | undefined): string {
  const list = (tools ?? []).map((t) => ({
    name: t.name,
    description: t.description ?? "",
    parameters: t.parameters ?? {},
  }));
  list.sort((a, b) => a.name.localeCompare(b.name));
  return createHash("sha256").update(JSON.stringify(list)).digest("hex");
}
```

Invalidation at pool-entry reuse time:
```ts
// Pi tool set changed → MCP server must be rebuilt.
if (entry && opts.mode === "pi-tools" && entry.toolsHash !== opts.toolsHash) {
  await destroyEntry(entry);
  entry = undefined;
}
```

**Flow:** each pi-tools stream call computes `toolsFingerprintOf(context)` → `getOrCreateEntry` compares it against the pooled entry's stored `toolsHash` → mismatch destroys the whole entry (session + board + MCP server) so the next pass rebuilds the MCP server from the NEW tool set; unchanged hash reuses the warm session.
**Invariant:** The hash is order-insensitive (hosts may reorder tools between calls without triggering churn) but sensitive to any name/description/parameter change. Invalidation is coarse-grained BY DESIGN — the session, board, and name maps are one consistent unit, so no stale alias map can survive a tool-set edit. Compare-then-destroy happens BEFORE any new turn starts, never mid-turn.
**Probe:** `test/pi-tools-bridge.test.ts:88-99` ("fingerprints tools stably"): `[b,a]` and `[a,b]` produce identical fingerprints.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "fingerprintTools toolsHash toolsFingerprintOf destroyEntry getOrCreateEntry", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt canonicalize(sort+normalize-missing)-then-hash as the cheap change detector for anything cached against a declarative set; adopt whole-unit invalidation when the cache is an interdependent bundle. Adapt the field list to whatever your downstream actually captures. Omit localeCompare if you need byte-stable ordering across locales (use a codepoint sort).
