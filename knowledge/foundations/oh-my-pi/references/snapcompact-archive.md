<!-- capsule-v2 -->
# Snapcompact archive — how a vision-compaction pass orchestrates and re-renders

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How does a local, deterministic compaction turn discarded conversation history into dense bitmap frames that a vision LLM reads back, and how does it survive repeated compactions without losing continuity?

## Compact orchestration
**Path/Symbol:** `packages/snapcompact/src/snapcompact.ts:compact` (2032–2180), `planArchive` (1910–1994), `getPreservedArchive` (1698–1728), `stripPreservedArchive` (1735–1741).
**Signature:** `compact<TMessage>(preparation: CompactionPreparation<TMessage>, options?: Options<TMessage>): Promise<CompactionResult>`.
**Data Shape:** `CompactionPreparation` = `{ firstKeptEntryId, messagesToSummarize, turnPrefixMessages, tokensBefore, previousSummary?, previousPreserveData?, fileOps }` → `CompactionResult = { summary, shortSummary?, firstKeptEntryId, tokensBefore, details?, preserveData? }`. The archive persists under `preserveData["snapcompact"]` as `Archive = { frames: Frame[], totalChars, truncatedChars, text?, textHead?, textTail? }`.

### Decisive source
```ts
// Re-compacting a snapcompacted history unfolds the prior archive's source
// text and treats it as one coherent transcript: the previous kept source
// ages in ahead of the new history, then the whole thing is re-rendered.
if (hasPreviousText) {
  archiveText = archiveText.length > 0 ? `${previousText}${NEWLINE_GLYPH}${archiveText}` : previousText;
}
// Data URLs must never reach planArchive: its edge slices are structure-blind...
archiveText = elideDataUrls(archiveText);
const layout = planArchive(archiveText, high, low, maxFrames);
```
`planArchive` keeps `TEXT_EDGE_PAGES * capHi` chars verbatim at the oldest edge (`textHead`) and newest edge (`textTail`), images the middle, and when the middle overflows `maxFrames` **foveates** it: `HQ_EDGE_FRAMES` (3) HQ pages at each edge, a denser low-quality tier in the middle, and drops the OLDEST dense slice to fit:
```ts
const middleBudget = maxFrames - 2 * imageEdgeFrames;
if (middlePages.length > middleBudget) {
  const dropped = middlePages.slice(0, middlePages.length - middleBudget).join("");
  truncatedChars = dropped.length;
  middleText = middleSource.slice(dropped.length);   // keep newest, drop oldest
  middlePages = middlePages.slice(middlePages.length - middleBudget);
}
```

**Flow:** serialize discarded messages → normalize → unfold prior kept source ahead of new history → elide data URLs → `planArchive` (text edges + foveated imaged middle) → re-render frames (carrying open dim span across every boundary) → build summary + `preserveData[PRESERVE_KEY]` archive. `maxFrames` is clamped to `MAX_FRAMES_DEFAULT` (80); a caller may only lower it, never raise it.

**Invariant:** the full kept source persists on the archive (`text`) so each later compaction unfolds and re-renders it coherently — the archive is never a pile of disjoint frames, but one re-renderable transcript. `stripPreservedArchive` returns `undefined` when nothing else remains so an empty `{}` is never persisted.

**Probe:** `packages/snapcompact/test/snapcompact.test.ts:962` ("re-renders later compactions from the kept source text" — second compact with `previousPreserveData` keeps the follow-up turn in `text`/`textTail` and still yields 5 frames); `:916` ("keeps plain text at both edges and images in the middle"); `:935` ("uses three HQ image frames on each edge when the budget allows" — cols[0..3] and cols[-3..] equal `hiCols`, cols[3] denser).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "compact planArchive snapcompact", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the re-render-from-kept-source invariant, the foveated HQ/LQ/HQ layout, and the oldest-slice-drop policy — these are the portable contracts a porter would get wrong (naive ports either re-summarize each pass, losing continuity, or drop the NEWEST frames, losing the most recent context). Adapt the native PNG rasterizer (`renderSnapcompactPng` in `crates/pi-natives/src/snapcompact.rs`) — any renderer that honors the `Frame` geometry + dim-ink toggles works. Omit provider-specific billing internals (covered in `snapcompact-shape-billing`). Coverage: both cited paths `no_recorded_issue` + `metadata_match` on the `oh-my-pi` full index.
