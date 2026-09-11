<!-- capsule-v2 -->
# Memory search result assembly — how do five query modes share one renderer, and what does a cold hit owe the caller?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how are matches grouped into segments, and when must a cold (digest) hit stay a pointer instead of pretending to be evidence?

## Mode matrix + segment flush boundaries + cold-pointer recipe
**Path/Symbol:** `src/memory/search.ts:searchMemoryIndex` (:390-470), `groupIntoResults` (:475-597), `compareSearchItems` (:599-615), regex plane `searchRegex` (:319-380) + `collectRegexTargets` (:272-317), digest scorer `scoreDigestTerms` (:214-257), formatter `formatSearchResult` (:634-675).
**Signature:** `searchMemoryIndex(shards, digests, query): Promise<SearchResult>`; `matchMode ∈ {browse, lexical, regex, structural, combined}`; candidate limits default 50k entries / 10k digests / 10k items.
**Data Shape:** SearchResult `{matchMode, matchedCount, totalItems, segmentCount, segments[], digestHits[], items[], queryCoverage{complete,reasons[]}}`; SearchSegment carries `entryRange`, per-entry `marker: ">" | " "`, exactMatches (`index`, entryId, operationAddress), lineage fields for re-hydration.

### Decisive source
```ts
const matchMode = plan.kind === "browse" ? (structurallyFiltered ? "structural" : "browse")
  : structurallyFiltered ? "combined" : plan.kind === "regex" ? "regex" : "lexical";
const entries: SearchSegmentEntry[] = current.map((entry) => {
  const matched = matchedSet.has(entry.index);
  return { entry, matched, marker: markOnlyMatches ? (matched ? ">" : " ") : ">" };
});
if (markOnlyMatches && matchedEntries.length === 0) { current = []; return; }   // drop empty segments
```
```ts
// cold hits are pointers with verification material, never content
  return `> session ${hit.sessionId} (cold, ${hit.cwd}, ${timestamp}, branches=${hit.branches}) ${match} — hydrate exact file ${JSON.stringify(hit.sessionFile)} with branches ${JSON.stringify(hit.branches)}, expectedSourceHash ${JSON.stringify(hit.sourceHash)}, and expectedLineageFingerprint ${JSON.stringify(hit.lineageFingerprint)}.`;
```

**Flow:** plan the query (browse/terms/regex via explicit mode) → dispatch: browse collects recents (score 0, or 1 under structural filters); lexical runs BM25 over hot entries + set-intersection scoring of cold vocabularies; regex builds a byte/term-bounded haystack list (hot entry texts first, then cold vocabulary terms ONLY if collection stayed complete — partial haystacks are flagged, never silently searched) and delegates to the sandboxed worker → located entries group by session in first-match order; a segment FLUSHES at every `user|bashExecution|compaction` boundary → items merge segments+digests under one comparator (score → mtime → entries-before-digests → index/file), sliced to maxItems; ANY truncation at any layer appends a named reason (`candidate_entry_budget`, `candidate_digest_budget`, `candidate_item_budget`, `cold_structural_filter_requires_hydration`, regex limits) into queryCoverage.
**Invariant:** coverage is honest by construction — an incomplete answer always says WHY in sorted reasons; cold vocabulary membership alone never claims an entry-level match ("hydrate to establish entry-level co-location"); structural filters on cold tiers can only count retained addresses, never fabricate text; empty-result messages distinguish no-scope / no-match / incomplete-coverage.
**Probe:** `tests/memory-cache-v6.test.ts:238` ("hydrates bounded ranges explicitly and expands by stable entry id" — pointer → scoped recall with expectedSourceHash+entryRange returns exactly entry 1 and writes NO shard cache), `:96` + `:170` in `tests/memory-trace-integration.test.ts` (filters/operation-address expansion/cold vocabulary; capability heads selected in both tiers without treating catalog prose as evidence).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "searchMemoryIndex groupIntoResults scoreDigestTerms collectRegexTargets compareSearchItems formatSearchResult", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mode-matrix dispatch, boundary-flushed segments, single merged comparator, and the cold-pointer-with-verification-material contract; adapt role names, budgets, and formatting verbs; omit BM25 constant tuning (K1.2/B0.75 live in memory-tiered-index's sibling `bm25Score`). Direct integration tests cited; graph coverage clean.
