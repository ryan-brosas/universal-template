<!-- capsule-v2 -->
# Write echo preview — every mutating tool returns a preview of the file it just changed

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory`. **Question:** When an agent tool mutates a file the model cannot see, how do you close the loop so the next tool call is made with accurate state instead of hallucinated content?

## Write echo preview
**Path/Symbol:** `index.ts` — `memory_write` daily branch (:1662–1695), long_term append (:1734–1751), overwrite (:1715–1731); `scratchpad` list/add/toggle/clear_done (:1786–1924); `memory_forget` removed-content preview (:2124–2148). Shared constants `RESPONSE_PREVIEW_MAX_LINES = 120` / `RESPONSE_PREVIEW_MAX_CHARS = 4_000` (:148–149); builders `buildPreview`/`formatPreviewBlock`.
**Signature:** `buildPreview(content, { maxLines, maxChars, mode }): PreviewResult`; `formatPreviewBlock(title, content, mode): string`.
**Data Shape:** `PreviewResult = { preview, truncated, totalLines, totalChars, previewLines, previewChars }`; per-mode choice: daily writes preview END (newest entries), MEMORY.md previews MIDDLE, scratchpad previews START.

### Decisive source
```ts
// memory_write daily (1664-1672): preview what's there BEFORE appending, then echo it
const existing = readFileSafe(filePath) ?? "";
const existingPreview = buildPreview(existing, {
  maxLines: RESPONSE_PREVIEW_MAX_LINES,
  maxChars: RESPONSE_PREVIEW_MAX_CHARS,
  mode: "end",                                   // daily = newest at bottom
});
const existingSnippet = existingPreview.preview
  ? `\n\n${formatPreviewBlock("Existing daily log preview", existing, "end")}`
  : "\n\nDaily log was empty.";                  // empty case is explicit, not silent

// memory_write long_term (1709-1713): only durable writes dirty the snapshot;
// daily writes rely on this echo instead — they never invalidate the KV cache
// Daily writes are high-frequency and already echoed via tool-call args.
snapshotDirty = true;   // long_term branch only
```

**Flow:** before each mutation the tool reads the current file and renders a bounded preview (mode matched to where new content lands); after writing, the result text embeds that block plus structured `details.existingPreview`; forget returns a START-preview of exactly what was removed. The model therefore always sees post-write reality within one turn without re-reading the file.

**Invariant:** every mutation result carries enough rendered context to plan the NEXT write correctly; previews are hard-capped (120 lines / 4 000 chars) so echoes can't blow the context budget; the preview mode tracks entry recency (end for append-only logs, start for checklists, middle for curated memory).

**Probe:** `test/unit.test.ts` — `memory_write tool`: `appends to existing daily log` (:858, Morning+Afternoon coexist), `includes session ID in metadata comment` (:868, `[mysessio]` first-8), `overwrites MEMORY.md` (:825, `<!-- last updated:` stamp); `scratchpad tool`: add/done/undo/clear_done describes (:904+); e2e tier: `testScratchpadCycle` (`test/e2e.ts:362`). Coverage caveat: `formatPreviewBlock` output text has no dedicated unit assertion; the bounded-preview contract is pinned via `preview-truncation.md` capsules' tests plus these integration sites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "buildPreview formatPreviewBlock existingPreview RESPONSE_PREVIEW_MAX_CHARS", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the echo contract: read-before-write, render a capped mode-matched preview into the tool result, and mark only cache-hostile (curated) writes dirty. Adapt caps and modes to your host's budget. Omit nothing — this is the portable write-visibility pattern.
