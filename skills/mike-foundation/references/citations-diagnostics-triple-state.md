<!-- capsule-v2 -->
# Citations diagnostics triple-state — was the CITATIONS block absent, broken, or empty?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How can a caller (and its logs) distinguish "the model cited nothing" from "the model tried to cite but emitted garbage"?

## parse returning diagnostics alongside results
**Path/Symbol:** `backend/src/lib/chat/citations.ts:185` (`CITATIONS_BLOCK_RE = /<CITATIONS>\s*([\s\S]*?)\s*<\/CITATIONS>/`), `:189` (`CitationParseDiagnostics`), `:195` (`parseCitationsWithDiagnostics`). Direct test: `src/lib/__tests__/citations.test.ts` ("parseCitationsWithDiagnostics" describe).
**Signature:** `parseCitationsWithDiagnostics(text) -> { citations, diagnostics: { hasBlock, rawLength, error } }`.
**Data Shape:** three observable states — `{hasBlock:false, rawLength:0, error:null}` (no tags); `{hasBlock:true, rawLength>0, error:"..."}` (tags present but JSON failed / not an array); `{hasBlock:true, rawLength>0, error:null}` with possibly-empty citations array (valid block, zero valid entries).

### Decisive source
```ts
const match = text.match(CITATIONS_BLOCK_RE);
if (!match) return { citations: [], diagnostics: { hasBlock: false, rawLength: 0, error: null } };
const parsed = JSON.parse(raw);
if (!Array.isArray(parsed)) return { ..., error: "CITATIONS block JSON was not an array." };
```

**Flow:** regex is non-greedy DOTALL so only the FIRST block parses → JSON.parse inside try → array check → per-entry normalize+filter. `error` carries the raw exception message verbatim for malformed JSON.
**Invariant:** An empty-but-valid block (`[]`) is a SUCCESS with zero citations — collapsing it into the no-block state would mislabel intentional no-citation answers as parse failures in telemetry. The streaming layer devLogs all four diagnostics fields per turn (`hasBlock/citationsBlockLength/parseError/parsedCitationCount`).
**Probe:** `grep -c 'it(' src/lib/__tests__/citations.test.ts | head -1` plus targeted greps: `grep -c "JSON was not an array" src/lib/__tests__/citations.test.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "parseCitationsWithDiagnostics CitationParseDiagnostics", limit: 10 });
```

## Verdict
Adopt the triple-state result shape as the parse contract; adapt field names/error copy; omit the specific tag vocabulary.
