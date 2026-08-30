<!-- capsule-v2 -->
# Snapcompact text normalization — font-aware folding, wrapping, and pagination for bitmap rendering

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How does a porter turn arbitrary LLM/tool text into the normalized, wrapped, and paginated cell-grid pages that a bitmap font renderer can print without corrupting layout or losing meaning?

## Normalize / wrap / paginate
**Path/Symbol:** `packages/snapcompact/src/snapcompact.ts:normalize` (1340–1342), `normalizeWithStats` (1277–1332), `foldToAscii` (1217–1232), `wrap` (1507–1541), `paginateCells` (1478–1499), `geometry` (1563–1571), `dimStopwords` (1385–1403), `scanRenderability` (1348–1355).
**Signature:** `normalize(text, options?: NormalizeOptions): string`; `wrap(text, width, wideCells?): string[]`; `paginateCells(text, capacity, cols, wideCells): string[]`; `geometry(shape, size?): Geometry`.
**Data Shape:** `Geometry = { cols, rows, capacity }`. `NormalizeOptions = { shape?: Pick<Shape,"font">, font? }`. `wideCells` is true for every font except `silver` (CJK glyphs span two cells in narrow bitmap shapes).

### Decisive source
```ts
// Collapse whitespace + zero-width format chars; a run containing a real line
// break becomes the NEWLINE_GLYPH ("█"), pure format chars vanish.
const collapsed = stripped
  .replace(COLLAPSIBLE, run => (LINE_BREAK.test(run) ? NEWLINE_GLYPH : /[^\p{Cf}]/u.test(run) ? " " : ""))
  .replace(EDGE_RUNS, "");
// Per-character fold: ASCII/Latin-1 kept; emoji folded to [OK]/[FAIL]/[WARN]…;
// box-drawing → | - +; NFKD-decomposed ASCII kept; everything else → "?" (counted).
```
`wrap` is a greedy word-wrap with no mid-word breaks (hard split only for width+ words), ported verbatim from `research/exp14_bestgpt.py`. `paginateCells` slices into pages of at most `capacity` grid cells, inserting a one-cell pad before a wide glyph that would straddle the right edge (mirrors native `place_cell`); a single char wider than the whole budget still rides its page and the renderer clips it. `dimStopwords` wraps each maximal alphabetic run that is a stopword in `DIM_ON`/`DIM_OFF`, skipping spans already dim (wrapping there would terminate the enclosing dim span early). `scanRenderability` reports `isSafe` = ≤5% of graphic chars hit the `?` fallback.

**Flow:** strip ANSI → collapse whitespace (line breaks → `█`) → per-char fold (emoji/box/NFKD) → `wrap` at column width → `paginateCells` into pages (doc shapes: `docPages` = wrap once then slice into pages of `2*rows` lines). `pageFinisher` re-opens a dim span a page boundary cut through, then applies stopword dimming AFTER pagination so capacity math never sees the markers.

**Invariant:** the visible glyph count is unchanged by dim markers (they are zero-width), and wide CJK glyphs occupy exactly two cells in both the JS capacity math and the native renderer — the two MUST stay in sync (`isWideCodePoint` mirrors `is_wide` in `crates/pi-natives/src/snapcompact.rs`), or layout and capacity disagree on cell counts.

**Probe:** `packages/snapcompact/test/snapcompact.test.ts:212` ("normalize" — whitespace/emoji/box-drawing folding), `:1227` ("dimStopwords" — dim spans pass through untouched), `:1255` ("wrap" — greedy no-mid-word-break wrap), `:1272` ("doc layout" — two-column pagination).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "normalize wrap paginateCells geometry dimStopwords", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whitespace-collapse + NFKD-ASCII-fold + emoji-fold pipeline and the two-cell-wide CJK invariant — a porter who naively renders raw text will corrupt layout (line numbers erased by whitespace collapse, wide glyphs overflowing cells). Adapt the specific stopword list and emoji fold table. Omit the native rasterizer; any renderer honoring the cell grid + `DIM_ON`/`DIM_OFF` + `NEWLINE_GLYPH` contracts works. Coverage: `no_recorded_issue` + `metadata_match` on the `oh-my-pi` full index.
