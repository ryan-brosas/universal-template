<!-- capsule-v2 -->
# Preview & truncation — bounded, mode-aware text previews that keep injected context in budget

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent truncate memory content for previews and context injection without losing the informative head/tail/middle, and how does it report the truncation honestly?

## Preview & truncation
**Path/Symbol:** `index.ts:normalizeContent` (180–182), `truncateLines` (184–204), `truncateText` (206–229), `buildPreview` (231–267), `formatPreviewBlock` (269–285), `formatContextSection` (287–296).
**Signature:** `buildPreview(content: string, {maxLines, maxChars, mode}): PreviewResult`; `formatPreviewBlock(label, content, mode): string`; `formatContextSection(label, content, mode, maxLines, maxChars): string`.
**Data Shape:** `TruncateMode = "start" | "end" | "middle"`. `PreviewResult = { preview, truncated, totalLines, totalChars, previewLines, previewChars }`. Per-section caps: scratchpad 2000/120, daily 3000/120, search 2500/80, long-term 4000/150; overall `CONTEXT_MAX_CHARS = 16_000`.

### Decisive source
```ts
// truncateLines middle (193-201): keep head+tail around a marker
if (mode === "middle" && maxLines > 1) {
  const marker = "... (truncated) ...";
  const keep = maxLines - 1;
  const headCount = Math.ceil(keep / 2);
  const tailCount = Math.floor(keep / 2);
  return { lines: [...lines.slice(0, headCount), marker, ...lines.slice(-tailCount)], truncated: true };
}

// buildPreview (231-267): line-truncate first, then char-truncate the joined text
const lineResult = truncateLines(lines, options.maxLines, options.mode);
const text = lineResult.lines.join("\n");
const charResult = truncateText(text, options.maxChars, options.mode);
// truncated = lineResult.truncated || charResult.truncated

// formatContextSection (287-296): empty → "" so absent sections vanish from context
if (!result.preview) return "";
const note = result.truncated
  ? `\n\n[truncated: showing ${result.previewLines}/${result.totalLines} lines, ${result.previewChars}/${result.totalChars} chars]` : "";
return `${label}\n\n${result.preview}${note}`;
```

**Flow:** (1) `buildPreview` normalizes (trims) content, splits to lines, applies line truncation by mode, then char truncation on the joined text. (2) `truncated` is the OR of both. (3) `formatContextSection` returns `""` for empty previews (so a missing memory file contributes nothing) and appends an honest `[truncated: …]` note. (4) `formatPreviewBlock` labels a preview with total line/char counts for tool responses.

**Invariant:** a preview never exceeds its `maxChars`/`maxLines` budget; `mode="middle"` preserves both the head and tail around a marker; an empty section contributes zero bytes to context; truncation is always reported (never silent).

**Probe:** `test/unit.test.ts` — `buildMemoryContext` describe (:551) exercises the per-section caps and the overall 16K cap with the `[truncated]` note; `memory_write tool` describe (:771) asserts the `Existing MEMORY.md preview` / `Existing daily log preview` snippets. Coverage caveat: `test/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "buildPreview truncateText truncateLines formatContextSection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the start/end/middle line+char truncation, the `PreviewResult` shape, the empty-section suppression, and the honest `[truncated]` note. Adapt the char/line caps and labels to the host. Omit nothing here — this is the portable preview core.
