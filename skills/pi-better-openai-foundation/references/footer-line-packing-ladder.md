<!-- capsule-v2 -->
# Footer line-packing ladder — how do you compose a single-line status bar (left stats + right model identity) that degrades gracefully instead of overflowing?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What is the exact fit/truncate order for packing left and right content into a fixed-width terminal line?

## Fit-then-degrade ladder
**Path/Symbol:** `index.ts:installFooter` render body (:973-1148); the stats-line ladder is :1043-1090; provider-count conditional :1065-1069; model+thinking+fast suffix assembly :1050-1062; extension-status lines :1101-1111; context-percent color tiers :1006-1021.
**Signature:** `render(width): string[]` — pure function of width + cached state; no I/O.
**Data Shape:** `statsLeft` = usage segments (`↑in ↓out RcacheRead WcacheWrite $cost`, zero-value segments OMITTED, cost shown also when subscription OAuth `(sub)` flag set) + context display; `rightSide` = `[({provider}) ]model[ fast][ • {thinkingLevel|thinking off}]`. All widths via ANSI-aware `visibleWidth`/`truncateToWidth`.

### Decisive source
```ts
let statsLeft = parts.join(" ");
let statsLeftWidth = visibleWidth(statsLeft);
if (statsLeftWidth > footerTextWidth) {                 // rung 0: left alone too wide
  statsLeft = truncateToWidth(statsLeft, footerTextWidth, "...");
  statsLeftWidth = visibleWidth(statsLeft);
}
...
if (totalNeeded <= footerTextWidth) {                   // rung 1: both fit → pad between
  statsLine = statsLeft + " ".repeat(footerTextWidth - statsLeftWidth - rightWidth) + rightSide;
} else {                                                // rung 2: overflow
  const availableForRight = footerTextWidth - statsLeftWidth - 2;
  if (availableForRight > 0) {
    const truncatedRight = truncateToWidth(rightSide, availableForRight, ""); // NO ellipsis on the right
    statsLine = statsLeft + " ".repeat(Math.max(0, footerTextWidth - statsLeftWidth
      - visibleWidth(truncatedRight))) + truncatedRight;
  } else {
    statsLine = statsLeft;                              // rung 3: right sacrificed entirely
  }
}
```

**Flow:** build left/right independently (zero-symbols dropped; provider prefix shown ONLY when `getAvailableProviderCount() > 1` AND it still fits at rung 1's budget check :1067) → measure with visibleWidth → walk the ladder top-down. Context percent renders `"?"` when unknown, and colors by tiers (>90 error, >70 warning). Pet placement may shrink `footerTextWidth` to reserve pet columns (:1036-1038) BEFORE this ladder runs.

**Invariant:** LEFT content is never sacrificed while ANY space remains — degradation order is pad-between → truncate-RIGHT-with-no-marker → drop-right-entirely → (only then) ellipsize-left. The right side truncates SILENTLY (empty marker): an ellipsis there would suggest a cut-off model name users can act on, while the model identity is recoverable elsewhere. Porters get this wrong by truncating both sides proportionally or padding after measuring the ANSI-encoded string instead of its visible width.

**Probe:** `tests/footer.test.ts:352` — status-widget path renders exactly `["gpt-5.6 fast"]` (fast suffix present, no provider prefix at count=1, dimmed via theme.fg), pinning the suffix/provider assembly that feeds this ladder; full-width fit/truncate branches are source-pinned (:1043-1090) with no direct width-matrix test — coverage caveat recorded here deliberately.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "installFooter footer render", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the asymmetric degrade ladder and visibleWidth discipline for any fixed-width chrome. Adapt segment vocabulary (tokens/cost/model fields) to your host. Omit pet-column reservation unless porting the pets plane.
