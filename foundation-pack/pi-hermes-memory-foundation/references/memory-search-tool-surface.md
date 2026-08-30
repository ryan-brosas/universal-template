<!-- capsule-v2 -->
# memory_search tool surface — empty-store and no-hit states return as structured success-with-guidance, never thrown, so the model keeps steering

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** A search tool backed by an FTS5 store can fail four ways (empty query, empty store, zero hits, real error) — what should the MODEL see in each case?

## registerMemorySearchTool
**Path/Symbol:** `src/tools/memory-search-tool.ts` (whole file, 83 L): registration (:17–43) with `promptSnippet` + three `promptGuidelines`, enum params via `StringEnum` (`target: memory|user|failure`, `category: failure|correction|insight|preference|convention|tool-quirk`), `limit` clamped client-side `Math.min(args.limit || 10, 20)` (:49); guard ladder :51–67; render loop :69–77; result envelope `{content:[{type:"text",text}], details: SearchResult}` on every path.
**Signature:** `execute(_id, {query, project?, target?, category?, limit?}) → {content, details}`.
**Data Shape:** `SearchResult = {success: boolean; count?: number; message?: string; output?: string}` — the SAME shape for failures and successes, discriminated by fields.

### Decisive source
```ts
if (!query || query.trim().length === 0)
  return text("query is required");                                   // success:false
if (getMemoryStats(dbManager).total === 0)
  return text("No memories in extended store yet. Use memory_add to store memories.");  // names the REMEDY TOOL
const results = searchMemories(dbManager, query, {...});
if (results.length === 0)
  return text(`No memories found matching "${query}". Try a different search term or broader query.`);  // success:true, count:0
```
Hit rendering labels each row with target emoji (👤 user / ⚠️ failure / 🧠 memory), `[project]` vs `[global]`, optional `[category]`, then `Created | Last used` — the same vocabulary the lookup normalizer strips on the way back in.

**Flow:** validate → cheap COUNT probe before any search → search (the fts5-search.md ladder handles syntax recovery internally) → format or guide. Every branch returns a well-formed tool result; NOTHING throws past argument validation.
**Invariant:** "no results" is DATA, not an exception — a throwing search teaches the model to fear the tool; a guided empty state teaches it the remedy (`memory_add`) or a better query. The empty-store probe runs BEFORE the search because its guidance differs fundamentally from no-match. Client-side limit clamping means the schema's contract holds even against a lying caller.
**Probe:** `tests/tools/memory-search-tool.test.ts` — "returns a broader natural-language match when strict term matching misses" (:23, drives the full searchMemories fallback through the tool). Coverage caveat: the three guard branches are exercised indirectly via store-level suites; tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "registerMemorySearchTool searchResultView getMemoryStats", limit: 5 })`

## Verdict
Adopt for any retrieval tool consumed by an LLM. Adapt enums and copy; keep the guard order (validate → empty-store → no-hit), remedy-naming messages, and throw-free structured envelopes. Omit nothing.
