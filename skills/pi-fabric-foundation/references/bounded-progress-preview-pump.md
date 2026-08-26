<!-- capsule-v2 -->
# Bounded progress-preview pump — how do you stream a child agent's live state into host UI without unbounded work per tick?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does a blocking `agents.run/wait` call publish cheap, bounded, diffed progress previews on a 1-second poll while the child keeps running?

## Revision-string dedupe over a depth/node-budgeted preview tree
**Path/Symbol:** `src/providers/agents-provider.ts:1021-1046` (`waitForResultWithProgress`), `:931-965` (`collectAgentToolPreviewNodes`), `:967-1019` (`attachAgentToolPreview`), `:1061-1068` (`agentProgressRevision`); driver `waitWithProgress` :1070-1121.
**Signature:** `waitForResultWithProgress<T>(result: Promise<T>, onProgress: () => void): Promise<T>`; `collectAgentToolPreviewNodes(records: readonly AgentRunRecord[], options: AgentToolPreviewTreeOptions, depth = 0, budget = { remaining: options.maxNodes ?? AGENT_PREVIEW_TREE_MAX_NODES }): FabricAgentToolPreviewNode[]`.
**Data Shape:** constants `AGENT_PROGRESS_INTERVAL_MS=1_000`, `AGENT_PREVIEW_TEXT_CODE_POINTS=2_000`, `AGENT_PREVIEW_TOOL_LIMIT=8`, `AGENT_PREVIEW_TREE_MAX_DEPTH=4`, `AGENT_PREVIEW_TREE_MAX_NODES=24`; preview `{kind:"fabric-agent-tools", id, name, status, runner, owner:"actor"|"agent", text?, tools[], agents?[], agentsTruncated?}`; revision strings like `"running:169…:Bash:12:3"` (status:updatedAt:currentTool:toolCalls:turns).

### Decisive source
```ts
// :1025-1045 — the timer NEVER outlives or races settlement
let settled = false;
const finish = (complete: () => void): void => {
  if (settled) return; settled = true;
  clearInterval(progressTimer); complete();
};
const progressTimer = setInterval(() => {
  if (settled) return;
  try { onProgress(); }
  catch (error) { finish(() => reject(error)); }   // a throwing probe FAILS the wait
}, AGENT_PROGRESS_INTERVAL_MS);
progressTimer.unref?.();
result.then((v) => finish(() => resolve(v)), (e) => finish(() => reject(e)));
// :1012-1014 — JSON-snapshot diffing keeps the poll a no-op when nothing moved
const revision = JSON.stringify(preview);
if (revision !== previousRevision) context.attachPreview(preview);
return revision;
// :939-946 — ONE shared budget object threads the whole recursion
if (budget.remaining <= 0) break;
budget.remaining -= 1;
const agents = depth + 1 < maxDepth && descendants.length > 0 && budget.remaining > 0
  ? collectAgentToolPreviewNodes(descendants, options, depth + 1, budget) : [];
```

**Flow:** `manager.wait(id)` starts → every 1s: read coarse status → build revision string → if changed, rebuild the bounded preview (tail-truncated text via `tailCodePoints` code-point-safe slice, ≤8 recent transcript tools read defensively — descendant cleanup mid-read returns `[]` — recursive nested-run tree under shared depth≤4 / nodes≤24 budget) → `context.attachPreview(preview)` + `context.update("Agent <name>: <status> · <tool>")` + activity metrics → on settle, `finally` attaches one FINAL preview and status line even after cancellation. Actor waits use the same pump with `actorWorker(manager, actorId, includeTerminal)` picking the running run or the LAST run in insertion order as terminal snapshot.
**Invariant:** the settled latch guarantees exactly one resolution and no post-settlement timers; a progress callback that throws rejects the whole wait (progress is load-bearing, not best-effort). Preview cost per tick is bounded three ways — text tail, tool count, and tree budget with an honest `agentsTruncated` flag whenever descendants were dropped by EITHER bound. The revision-diff means unchanged ticks do zero UI work.
**Probe:** `tests/agents-provider.test.ts:1332-1426` unit block pins the tree contract directly: `:1357` recursive mapping, `:1385` depth overrun sets `agentsTruncated:true` and drops grandchildren, `:1403` `maxNodes:2` caps breadth mid-tree with the flag set, `:1418` actor-owned runs get `owner:"actor"` + actorName; integration `:759` "refreshes bounded agent previews when only the transcript changes".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "collectAgentToolPreviewNodes nested preview budget", limit: 10, fields: ["signature", "name", "file"] });
```
(Rank#1 line-exact :931-965; `waitForResultWithProgress` resolves rank#1 on its own name.)

## Verdict
Adopt the whole pump for any long-blocking agent/tool call that must show live child state: settled-latch interval, revision-string dedupe, budget-bounded tree, defensive transcript reads, guaranteed final paint in `finally`. Adapt budgets to your UI's payload limits; keep them as named constants so tests can pin them. Omit the fabric-specific preview envelope shape if your host has its own widget protocol.
