<!-- capsule-v2 -->
# Inline pet footer composition — how do you place an animated terminal image beside text rows without breaking cursor state?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What are the layout rules for merging image-bearing lines with plain text lines in a fixed-width footer?

## Footer composition
**Path/Symbol:** `src/footer-layout.ts:combineInlinePetFooter` (:63-97); helpers `isTerminalImageLine` (:31-33), `petLineCell` (:35-40), cursor-strip pair (:42-54), `terminalImageInlineLeftSequence` (:56-61); placement predicates :15-21.
**Signature:** `combineInlinePetFooter(petLines, textLines, width, placement, petWidth): string[]`.
**Data Shape:** Image protocols detected by payload markers: kitty `\x1b_G` or iTerm `\x1b]1337;File=`; placements inline-left|inline-right|badge|stacked|habitat.

### Decisive source
```ts
const renderPetOnRight =
  placement === "inline-right" || (placement !== "inline-left" && hasTerminalImageLine);
const leftImageLine = placement === "inline-left" ? petLines.find(isTerminalImageLine) : undefined;
...
const petPart = leftImageLine ? spaces(petWidth) : petLineCell(petLine, petWidth);
if (renderPetOnRight)
  lines.push(`${padTextToWidth(textPart, textWidth)}${spaces(gap)}${petPart}`);
else lines.push(`${petPart}${spaces(gap)}${textPart}`);

// LEFT-side images cannot be padded like text — reserve blank space and re-emit:
if (leftImageLine && lines.length > 0)
  lines[lines.length - 1] += terminalImageInlineLeftSequence(leftImageLine, totalRows);
```
Cursor arithmetic: image lines carry their own `[nA`/`[nB` move wrappers which are STRIPPED (`stripLeadingCursorUp`/`stripTrailingCursorDown`) and rebuilt against totalRows so the image lands on the last row while earlier rows stay reserved-blank.

**Flow:** detect image protocol from pet line payloads → choose side (image lines force right unless explicitly inline-left) → pad/clip each row to petWidth+gap+textWidth exactly → append rebalanced cursor-wrapped image sequence on the final row for left placement.
**Invariant:** Every output row is EXACTLY width cells (test-pinned visibleWidth); image lines are never width-padded as if they were glyphs — they get blank reservation + deferred sequence emission, because terminals treat embedded graphics as cursor-invisible.
**Probe:** `tests/footer-layout.test.ts` (:13 badge cap 6, :18 left `"P   abc..."` vs right `"abc...  P "` both exact-width, :30 both protocol markers recognized).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "combineInlinePetFooter isTerminalImageLine stripLeadingCursorUp", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exact-width row composition + image-lines-are-not-glyphs handling. Adapt gap/placement names. Omit nothing — this module is fully portable TUI craft.
