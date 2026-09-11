<!-- capsule-v2 -->
# Compaction — cut legally, then reduce only cheap history

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How can local context shrink without orphaning tool results or invalidating prompt caches?

## Legal cuts precede budget choice
**Path/Symbol:** `packages/agent/src/compaction/compaction.ts:findValidCutPoints` (415–450), `findCutPoint` (499–570), `findTurnStartIndex` (457–475).
**Signature:** `findCutPoint(entries, tokenizer, startIndex, endIndex, keepRecentTokens): CutPointResult { firstKeptEntryIndex, turnStartIndex, isSplitTurn }`.
**Data Shape:** session entries → role/type-legal index set → backward token walk over `tokenizer.countMessage`.

### Decisive source
```ts
case "user": case "assistant": case "bashExecution":
case "hookMessage": case "branchSummary": case "compactionSummary":
  cutPoints.push(i); break;
case "toolResult": break;                       // never start retained history at a result
...
for (let i = endIndex - 1; i >= startIndex; i--) {
  accumulatedTokens += tokenizer.countMessage(entry.message);
  if (accumulatedTokens >= keepRecentTokens) {
    for (const c of cutPoints) if (c >= i) { cutIndex = c; break; }  // snap FORWARD to a legal cut
    break;
  }
}
while (cutIndex > startIndex) {                 // back off over adjacent non-message state
  const prev = entries[cutIndex - 1];
  if (prev.type === "compaction" || prev.type === "message") break;
  cutIndex--;
}
const turnStartIndex = isUserMessage ? -1 : findTurnStartIndex(entries, cutIndex, startIndex);
```

**Flow:** enumerate legal boundaries → walk backward accumulating estimates → snap forward to the nearest legal cut ≥ the budget-exceeding entry → include adjacent non-message entries → classify split-turn vs clean user-message start.
**Invariant:** retained history never begins at a tool result; a split turn keeps its `turnStartIndex` so the summarized half is tracked, never silently discarded.
**Probe:** direct `packages/agent/test/compaction-reserve-provenance.test.ts:13–92` proves threshold/reserve provenance is distinct from cut legality; `compaction-boundary.test.ts` covers boundary interactions.

## Prune and shake only cold, mutable suffixes
**Path/Symbol:** `compaction/pruning.ts:pruneSupersededToolResults` (251+), `pruneToolOutputs` (311–430, warm guard 343–369); `compaction/shake.ts:collectShakeRegions` (305–363).
**Signature:** both take `(entries, tokenizer, config)`; shake returns regions, apply mutates.
**Data Shape:** keep-boundary id, `protectTokens`, `cacheWarmSuffixTokens`, protected-tool set, supersede key, `useless` flag, `prunedAt`, `minSavings`.

### Decisive source
```ts
// pruneToolOutputs — cache-stable guard:
const messageSuffix = cacheWarmSuffixTokens === undefined ? undefined : computeMessageSuffixTokens(entries, tokenizer);
const inWarmPrefix = messageSuffix !== undefined && cacheWarmSuffixTokens !== undefined
  && messageSuffix[i] > cacheWarmSuffixTokens;
if (inWarmPrefix || i < boundaryIndex) continue;   // rewriting cached prefix costs more than savings
```
```ts
// collectShakeRegions — eligibility ladder:
if (i < boundaryIndex) continue;                   // pre-boundary entries are summarized away anyway
const uselessResult = toolResult?.useless === true && toolResult.isError !== true;
if (!uselessResult && accumulatedAfter[i] < config.protectTokens) continue; // protect recent tail
if (toolResult.prunedAt !== undefined) continue;   // already pruned
if (isProtectedToolResult(...)) continue;
...
if (savings < config.minSavings) return [];        // whole batch no-ops below floor
```

**Flow:** reject pre-boundary and warm-prefix entries → respect protected/recent/already-pruned results → require aggregate savings above `minSavings` → mutate and `invalidateMessageCache(message)` so stale token estimates cannot leak into later cuts.
**Invariant:** a superseded/useless result is still preserved when rewriting its cached prefix costs more than its savings; toolCall blocks are never touched and regions never cross message boundaries.
**Probe:** direct `supersede-prune.test.ts:537–563` — deep superseded result is rewritten WITHOUT the guard but kept WITH `cacheWarmSuffixTokens`; `shake.test.ts:74–193` covers protected/recent/already-pruned skips, minSavings gating, and fenced-block conservatism.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(findValidCutPoints|findCutPoint|findTurnStartIndex|pruneToolOutputs|collectShakeRegions)$", limit: 12, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.agent.src.compaction.pruning.pruneToolOutputs" });
```

## Verdict
Adopt legality-first cutting (tool-result boundaries sacred), forward-snap to legal cuts, warm-prefix cache protection, and minSavings-gated batch mutation; adapt entry-type taxonomy and notice strings to host session shapes; omit OpenAI/V2 remote paths (covered by replay-and-occupancy.md). Coverage caveat: tests excluded from graph index by design; probes are source-grounded from on-disk test files.
