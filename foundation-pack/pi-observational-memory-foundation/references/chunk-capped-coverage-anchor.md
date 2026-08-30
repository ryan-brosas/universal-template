<!-- capsule-v2 -->
# Chunk-capped coverage anchor — the clock advances to the last serialized id, never to the backlog tail

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** When the serialized backlog had to be truncated to fit the worker model's window, how far may the coverage clock advance — and what happens on the next run?

## Path/Symbol
**Path:** `src/hooks/consolidation-trigger.ts` (`runObserverStage` :255-288)
**Symbols:** resolve-before-budget ordering :255-258, contextWindow read + cap :267-268, serialize destructure :269-274, empty-chunk guard :275-277, `coversUpToId = sourceEntryIds.at(-1)` :276, `observer.chunk_capped` debug event :279-288.

**Signature:** `const coversUpToId = sourceEntryIds.at(-1)` — the LAST id the serializer actually shipped, not `backlogEntries.at(-1)`.

**Data Shape:** `serializeSourceAddressedBranchEntries(backlogEntries, { maxTokens }) → { text, sourceEntryIds[], estimatedTokens, truncatedSourceEntryIds[] }`; `sourceEntryIds` doubles as the observer's allowlist AND the coverage anchor set.

### Decisive source
```ts
// Resolve the model before building the chunk: the default chunk cap
// derives from the resolved model's context window.
const resolved = await resolveModel("observer");
if (!resolved) return "abort";

const lastCoverageIdx = latestCoverageIndex(entries, OM_OBSERVATIONS_RECORDED);
const backlogEntries = sourceEntriesAfter(entries, lastCoverageIdx);
const contextWindow = (resolved.model as { contextWindow?: number }).contextWindow;
const maxChunkTokens = resolveObserverChunkMaxTokens(runtime.config, contextWindow);
const { text: chunk, sourceEntryIds, estimatedTokens: chunkTokens, truncatedSourceEntryIds } =
	serializeSourceAddressedBranchEntries(backlogEntries, { maxTokens: maxChunkTokens });
if (!chunk.trim() || sourceEntryIds.length === 0) return "continue";
const coversUpToId = sourceEntryIds.at(-1);
if (!coversUpToId) return "continue";
```

**Flow:** model resolved FIRST (the cap needs its window) → backlog = source entries strictly after current observation coverage → serialize under cap → nothing rendered or no ids ⇒ continue WITHOUT arming backoff or coverage → anchor = last serialized id → if anything was left out (`sourceEntryIds.length < backlogEntries.length || truncatedSourceEntryIds.length > 0`) emit `observer.chunk_capped` with both sides' counts → records append with `coversUpToId = anchor` → NEXT run resumes strictly after the anchor.

**Invariant:** Coverage means "what a worker actually SAW", so a capped run advances the clock only to the chunk tail — the remainder drains incrementally across runs instead of being silently marked covered. The oversized-FIRST-entry case still anchors at that entry's own id: the head/tail excerpt keeps provenance truthful (the id points at the full ledger entry), and the test proves the following run starts AFTER it rather than retrying the un-shrinkable input forever. An unresolvable/empty anchor skips all writes; nothing partial ever arms the backoff or fakes coverage ("observer no-output appends nothing and does not fake observation coverage").

**Probe (direct tests):**
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
npx vitest run tests/consolidation-trigger.test.ts   # describe "observer chunk cap":
# :674 3×800-char backlog @256-token cap ⇒ run1 allowedSourceEntryIds ["raw-1"], coversUpToId
#   "raw-1"; run2 (in-flight cleared) resumes at raw-2 — incremental drain pinned end-to-end.
# :701 one oversized tool result ⇒ head/tail excerpt contains HEAD:/middle-omitted/:TAIL,
#   allowedSourceEntryIds ["raw-huge"], coversUpToId "raw-huge", next run starts after it.
# :746 cap derived from resolved model when unconfigured: contextWindow 1280 ⇒ floor(1280*0.2)
#   = 256 ⇒ only raw-1 fits.
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "sourceEntriesAfter coversUpToId observer.chunk_capped resolveObserverChunkMaxTokens", limit: 10 });
```

**Verdict:** Adopt saw-toothed coverage: anchor at the last serialized id, drain the remainder across runs, log capping with explicit before/after counts, and derive the cap from the resolved model's window. Adapt budget arithmetic to your tokenizer. Omit nothing behavioral — the anchor choice is what makes truncated input safe.
