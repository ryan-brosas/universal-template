<!-- capsule-v2 -->
# Alt-screen transcript search — how does search match across wrapped lines AND highlight at the right screen columns?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter searches the visible scrollback and matches spanning line breaks fail or highlight the wrong cells — what data structure fixes both?

## One corpus string + a per-character source map
**Path/Symbol:** `packages/tui/src/alt-screen-search.ts` (157L; appendMappedText :26-30, corpus build :36-51).
**Signature:** corpus = `{ text: string; source: Array<SearchSourceSpan | undefined> }` — one flat searchable string with a parallel array mapping EVERY character back to (row, startCol, endCol).
**Data Shape:** Whitespace runs collapse to single separators carrying NO source map, so `foo bar` matches `foo⏎bar`. Map entries carry width-correct columns (grapheme segmentation + visibleWidth per grapheme — CJK/emoji land on correct columns); adjacent same-row segments coalesce into one highlight rectangle.

### Decisive source
```ts
corpus.text += text;
for (let index = 0; index < text.length; index++) corpus.source.push(span);
// separator path:
if (corpus.text.length > 0) pendingSeparator = true;
appendMappedText(" ", undefined, corpus);   // mapless whitespace separator
```
The user's query is always compiled as an ESCAPED LITERAL regex — users never get regex semantics by accident.

**Flow:** render rows → append each row's text to the corpus with its span map → collapse whitespace between rows into mapless separators → run match → map every matched character through `source` to screen rectangles → merge adjacent same-row rectangles for stable highlights. Search bar renders inverted: label left, N/M count right-justified.
**Invariant:** Match positions are never stored as raw string indexes of any single row — every highlight must round-trip through the per-character source map, which is what makes cross-line matches and wide glyphs both land correctly.
**Probe:** No dedicated test file at this HEAD (`test/` has no alt-screen-search suite) — coverage caveat; deterministic probes: corpus/map construction at :26-51 verbatim.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "corpus SearchSourceSpan alt-screen search", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mapped-corpus structure wholesale — it is small and self-contained. Adapt rectangle merging to your cell grid. Omit regex escaping if your search is already literal. Coverage caveat: untested upstream at this HEAD.
