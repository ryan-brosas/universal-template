<!-- capsule-v2 -->
# Citation tolerant normalizer — how do you survive LLM-shaped citation JSON without dropping valid entries?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** What normalization ladder turns the model's freeform `<CITATIONS>` payloads into typed citations while rejecting only truly unusable entries?

## Per-entry normalize-or-null with alias and casing tolerance
**Path/Symbol:** `backend/src/lib/chat/citations.ts:46` (`normalizeCitation`), `:104` (`normalizeCellLocator`), `:113` (`normalizeCitationPage`), `:125/:149` (document/case quote normalizers). Direct test: `backend/src/lib/__tests__/citations.test.ts`.
**Signature:** `normalizeCitation(raw: unknown) -> ParsedCitation | null`; kind = case if finite `cluster_id > 0` else document (requires string `doc_id`).
**Data Shape:** ParsedDocumentCitation carries BOTH legacy top-level `{page,quote,sheet?,cell?}` AND a `quotes[]` array (≤3, each `{page,quote,sheet?,cell?}`); case quotes carry `{opinionId|null,type|null,author|null,quote}`.

### Decisive source
```ts
const markerRef = typeof c.marker === "string"
    ? Number(c.marker.match(/^\[(\d+)\]$/)?.[1]) : NaN;   // "[3]" → 3
const ref = typeof c.ref === "number" ? c.ref
    : Number.isFinite(markerRef) ? markerRef : null;      // ref OR [N] marker
const quote = typeof c.quote === "string" ? c.quote : c.text; // field alias
// cluster ids: number OR camelCase clusterId OR numeric STRING; >0 only;
// fractional ids FLOOR to int — non-positive falls through to document kind.
```

**Flow:** ref resolution → kind dispatch on cluster id → quotes array (slice(0,3), rows must be objects with non-empty text) → per-quote page normalization: numbers kept verbatim, `"12-13"` range strings kept as strings, junk parses via parseInt else defaults to **1** → spreadsheet locators `{sheet,cell}` fall back from row-level to TOP-LEVEL values so one citation can set sheet/cell once for all quotes → empty quotes array falls back to synthesing one quote from the top-level fields.
**Invariant:** Entries are dropped (not thrown) when unusable: no ref/marker, no doc_id, no quote text anywhere, or a case citation with zero quotable content after filtering. Valid siblings survive malformed ones (`parsed.map(normalize).filter(non-null)`).
**Probe:** `grep -c 'it(' src/lib/__tests__/citations.test.ts` → 29 incl "derives ref from a [N] marker when ref is missing", "normalizes pages: numbers kept, ranges kept, junk becomes 1", "treats non-positive cluster ids as document citations".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "normalizeCitation citations parseCitations", limit: 10 });
```

## Verdict
Adopt drop-don't-throw entry normalization + alias/case/str-format tolerance + bounded quote arrays with locator inheritance; adapt the accepted field names to your prompt contract; omit the specific spreadsheet A1 semantics if you have no cell-addressed sources.
