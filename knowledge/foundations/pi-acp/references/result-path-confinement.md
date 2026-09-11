<!-- capsule-v2 -->
# IDE tool-result confinement — how do you catch a path leaking OUT of the project root inside a tool RESULT, not just in its args?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you scan structured tool results for out-of-root paths (including symlink escapes through nearest-existing-ancestor realpath) under a bounded budget, and what differs between prefer and required modes?

## filterIdeResult — result-side confinement
**Path/Symbol:** `src/pi-extension/acp-mcp-bridge.ts` (`filterIdeResult` :706-786, `isInside` :1156-1168, `nearestExistingAncestor` :1171-1179) + `callRemoteTool` filter hook :671.
**Signature:** `function filterIdeResult(tool: BridgeTool, result: PiMcpToolResult, mode: IdeCodingMode, root: string | undefined, rawStructured?: unknown): PiMcpToolResult`.
**Data Shape:** scan budget `{ nodes: 5000 }`, depth cap 16; candidate strings harvested from values under `RESULT_PATH_KEYS` keys plus nested objects/arrays; relative candidates resolved against the project root; violation annotation lands in `result.details.composite.outOfRootResult` / `unconfinedResult:'truncated'`.

### Decisive source
```ts
for (const entry of candidates) {
  if (entry === '') continue
  const candidate = isAbsolute(entry) ? resolve(entry) : resolve(rootResolved, entry)
  if (!isInside(rootResolved, candidate)) { hit = true; break }
  if (realRoot !== undefined) {
    const existingAncestor = nearestExistingAncestor(candidate)
    if (existingAncestor !== undefined) {
      const real = tryRealpath(existingAncestor)
      if (real !== undefined && !isInside(realRoot, real)) { hit = true; break }
    }
  }
}
if (hit && mode === 'required') throw new McpToolError('IDE tool returned a path outside the project root', { code: 'out_of_root_result' })
```

**Flow:** applied AFTER `mcpResultToPiResult` mapping on every bridged call when ide-mode ≠ off and the tool is NOT itself a mutation tool (mutations are audited by provenance instead); truncated scans (depth/nodes exhausted) are themselves treated as a violation class — `required` throws `out_of_root_result`, `prefer` annotates. The symlink check walks UP from each candidate to its nearest EXISTING ancestor and realpaths that, so a path pointing through a not-yet-created link chain is still caught against the real root.
**Invariant:** arg-side confinement (`confineToolArgs`) and result-side scanning are SEPARATE passes — results can reference files args never mentioned; mutation tools are exempt from result filtering because their affected paths flow through the mutations_applied ledger; budget exhaustion must never silently pass in required mode.
**Probe:** `npx tsx --test test/unit/gate-hardening.test.ts` (confinement + escape matrices) — executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "filterIdeResult isInside nearestExistingAncestor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt result-side path scanning with node/depth budgets where exhaustion fails closed, and ancestor-realpath symlink checks symmetric with arg confinement. Adapt the path-bearing key vocabulary to your tool schemas. Omit for read-only tool surfaces with no filesystem semantics. Direct tests executed green at pin.
