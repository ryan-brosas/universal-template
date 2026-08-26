<!-- capsule-v2 -->
# Source-addressed serialization — labeled blocks, whole-entry-first packing, single pathological-entry excerpt

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you feed a bounded LLM call the unbounded session backlog while preserving exact provenance ids?

## Chunk packer (`src/serialize.ts`)
**Path/Symbol:** `serialize.ts:199-236` (`serializeSourceAddressedBranchEntries`), `serialize.ts:176-187` (`truncateSourceBlockToTokenBudget`), `serialize.ts:72-96,141-159` (`serializeConversation`, `serializeBranchEntries`).
**Signature:** `serializeSourceAddressedBranchEntries(entries: RenderableEntry[], options?: { maxTokens?: number }): { text, sourceEntryIds[], estimatedTokens, truncatedSourceEntryIds[] }`.
**Data Shape:** each block = `` `[Source entry id: ${entry.id}]\n${rendered}` ``; rendered forms `[User @ time]:`, `[Assistant @ time]:`, `[Tool result for <name> @ time]:`, `[Custom (type) @ time]:`, `[Branch summary @ time]:`.

### Decisive source
```ts
if (maxTokens !== undefined && estimatedTokens + blockTokens > maxTokens) {
	if (blocks.length > 0) break;                       // complete entries stay intact; later ones wait
	const excerpt = truncateSourceBlockToTokenBudget(label, rendered, maxTokens);
	if (!excerpt) break;                                // budget can't even fit the label → nothing
	blocks.push(excerpt);
	sourceEntryIds.push(entry.id);
	truncatedSourceEntryIds.push(entry.id);             // the ONLY case an entry is partially sent
	estimatedTokens = estimateStringTokens(excerpt);
	break;
}
```
```ts
const SOURCE_OMISSION_MARKER =
	"\n\n[… middle omitted: source exceeds observer input budget; original source remains in the session ledger …]\n\n";
// head/tail split at maxChars = maxTokens * 4 (≈ chars/token)
```

**Flow:** iterate oldest→newest source-renderable entries with an id → render each to a labeled block → accumulate while under budget → on overflow: if earlier blocks exist, STOP (remainder drains next run); if this is the FIRST entry and alone oversized, emit a marked head/tail excerpt so one pathological tool result cannot permanently block coverage; original ledger entries are never modified.
**Invariant:** Only the FIRST entry may ever be truncated; every other entry ships whole or waits. `sourceEntryIds` is the exact allowed-id set handed to the observer's validator — provenance flows from serializer to schema validation in one chain. Omission is loudly marked inside the text (the model sees what it didn't see). Empty renders are skipped entirely.

## Model-side cap (`src/config.ts`)
**Path/Symbol:** `config.ts:90-129` (`resolveObserverChunkMaxTokens`, constants).
**Signature:** `resolveObserverChunkMaxTokens(config, contextWindow): number`.

### Decisive source
```ts
export const OBSERVER_CHUNK_FALLBACK_MAX_TOKENS = 60_000;
export const OBSERVER_CHUNK_MIN_TOKENS = 256;
// ~4 chars/token estimate can undercount real tokens by up to ~4x on non-ASCII,
// so 0.2 keeps even the worst case at ~80% of the window.
export const OBSERVER_CHUNK_CONTEXT_RATIO = 0.2;
if (typeof contextWindow === "number" && ...) return Math.max(MIN, Math.floor(contextWindow * 0.2));
return OBSERVER_CHUNK_FALLBACK_MAX_TOKENS;
```

**Flow:** explicit config wins → else floor(0.2 × resolved model context window) → else 60k fallback; always ≥ 256.
**Invariant:** Without a cap, a backlog that outgrew the model window (repeated failures, mid-session enablement) makes EVERY observer call fail forever — the cap converts that into oldest-first draining across runs. The 0.2 ratio bakes in worst-case estimator error.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "serializeSourceAddressedBranchEntries truncateSourceBlockToTokenBudget resolveObserverChunkMaxTokens serializeBranchEntries", limit: 10 });
```
(Direct tests: `tests/source-serialization-budget.test.ts` :32 all-fit preserved, :48 later-complete-entries-wait, :61 no-source-rather-than-truncated-label, :75 marked head/tail excerpt; `tests/observer-chunk-cap.test.ts` pins the cap resolution.)

## Verdict
Adopt id-labeled source blocks, whole-entry packing with first-entry-only head/tail excerpting, explicit in-text omission markers, and the context-window-derived chunk cap. Adapt label formats, the 4-chars/token constant, and the 0.2 ratio to your tokenizer/model. Omit the recall-format renderers unless you build evidence recovery too.
