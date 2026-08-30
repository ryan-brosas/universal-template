<!-- capsule-v2 -->
# CourtListener turn cache — how does opinion text get cached per turn so find/read/verify never re-fetch?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How do search-result metadata, fetched opinions, and verified citations share ONE turn-scoped case store with first-field-wins merging?

## casesByClusterId upsert + HTML-to-text normalization + gated multi-opinion reads
**Path/Symbol:** `backend/src/lib/chat/tools/courtlistenerTurnState.ts:96` (`upsertCourtlistenerCases`), `:219` (`cachedCaseOpinionTexts`), `:240` (`getCachedCaseOpinionTexts`); consumer gating at `toolDispatcher.ts:1017-1042` (find-before-fetch veto) and `:1140-1184` (opinion-id gate). Direct test: `src/lib/chat/tools/courtlistenerTurnState.test.ts` (3 cases).
**Signature:** `upsertCourtlistenerCases(state, inputs) -> records[]`; state = `{casesByClusterId: Map<number, CourtlistenerCaseRecord>}` created once per runLLMStream call and threaded through every tool batch.
**Data Shape:** record `{clusterId, caseName, citations[], url, pdfUrl, dateFiled, opinions?}`; cached opinion text `{opinion_id|null, type|null, author|null, url|null, text}` where text prefers the plain `text` field else HTML→text via html-to-text (script/style skipped, whitespace collapsed).

### Decisive source
```ts
const nextCitations = [...current.citations, ...(input.citation ? [input.citation] : []), …]
    .map(nonEmpty).filter(Boolean);
const record = { …current,
    caseName: current.caseName ?? nonEmpty(input.caseName),   // FIRST non-empty wins; later never overwrites
    citations: Array.from(new Set(nextCitations)),            // dedup across verify+get paths
    url: current.url ?? nonEmpty(input.url), …,
    opinions: input.opinions?.length ? input.opinions : current.opinions };  // freshest NON-EMPTY payload wins
```

**Flow:** get_cases fetch → per-case SSE `case_opinions` events → upsert into turn cache → find_in_case searches CACHED texts only ("Case has not been fetched in this turn" error otherwise) and spreads remaining maxResults across opinions → read_case returns ALL opinions only when there's exactly one, otherwise demands explicit opinionId(s) and returns metadata-only rows with a next_required_action nudge toward 1-3-word probes → verify_citations ALSO upsert its citationLinks so later document-style citations resolve.
**Invariant:** Opinion TEXT is server-side-only — the model never receives full opinion bodies via get_cases, only char counts; the cache is the single path to bytes. Merging is asymmetric on purpose: identity fields lock on first sighting while opinions refresh whenever a newer non-empty payload arrives.
**Probe:** `cd backend && bunx vitest run src/lib/chat/tools/courtlistenerTurnState.test.ts` → 3 passed at pin; `grep -c 'Call courtlistener_get_cases first' src/lib/chat/tools/toolDispatcher.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "upsertCourtlistenerCases cachedCaseOpinionTexts courtlistener", limit: 10 });
```

## Verdict
Adopt turn-scoped entity caches + first-wins merge with refreshable payloads + token-gated bulk reads as portable contracts; adapt provider API shapes; omit CourtListener field specifics.
