<!-- capsule-v2 -->
# ANSI-aware terminal width math — how do you measure and truncate a styled string to exact visible columns?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** How do you count the terminal columns a formatted (ANSI-colored, emoji-bearing) string actually occupies, and cut it without ever overflowing?

## termVisWidth + truncateAnsi
**Path/Symbol:** `status.ts:204-234` (`EMOJI_RE`, `AMBIGUOUS_WIDE`, `termVisWidth`), `status.ts:236-267` (`truncateAnsi`).
**Signature:** `termVisWidth(str: string): number`; `truncateAnsi(str: string, maxCols: number): string`.
**Data Shape:** pure string → number / string. ANSI SESC sequences are detected by hand-rolled scanning: `0x1b` `[` then params `0x20–0x3f` and intermediates/finals `0x30–0x3f`.

### Decisive source
```ts
const EMOJI_RE = /\p{Emoji_Presentation}/u;
// East-Asian-Ambiguous glyphs some terminals render as 2 columns. ◆ is NOT
// listed: pi widths it as 1 here, and counting it wide leaves a trailing gap
// before the right edge.
const AMBIGUOUS_WIDE = new Set(["■", "▲", "◉"]);

// inside termVisWidth:
if (cp >= 0x1f1e6 && cp <= 0x1f1ff) width += 1;   // regional indicators = 1
else if (EMOJI_RE.test(char))       width += 2;   // Emoji_Presentation = 2
else if (AMBIGUOUS_WIDE.has(char))  width += 2;
else                                width += 1;
```
And truncation keeps escape codes intact while cutting printable chars at `maxCols - 1` and appending `"…"`:
```ts
const target = maxCols - 1;
... if (visWidth + charWidth > target) break;
return result + "…";
```

**Flow:** measure per code point (surrogate pairs consumed as one unit via `cp > 0xffff ? 2 : 1`) skipping CSI sequences entirely; truncation walks the same classification, copying escapes verbatim (they cost nothing), stopping before exceeding target, appending ellipsis.
**Invariant:** width of an ANSI-wrapped string equals width of its bare content ("ANSI is zero-width"). The ambiguous-width set is a HOST DECISION tuned to pi's own width function — ◆ deliberately counts NARROW because counting it wide leaves a trailing gap before the right edge in this TUI class. A porter must re-tune `AMBIGUOUS_WIDE` against their host's renderer or accept misalignment. Truncation reserves one column for "…" so output never exceeds maxCols.
**Probe:** `tests/status.smoke.ts` pins all of it: `:86` ANSI zero-width, `:87` `◆` narrow, `:88` `⚡`=2, `:89-92` truncate behaviors incl. `termVisWidth(truncateAnsi(...)) === 8` exact-fit and `maxCols<=0 ⇒ ""`. GREEN via `node tests/status.smoke.ts` on Node 26.7.0 at HEAD 4520704.
**Coverage caveat:** none for this module — direct test exists.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "termVisWidth", limit: 5 });
// → pi-hypercharm-provider.status.termVisWidth status.ts
```

## Verdict
Adopt both functions wholesale for any below-editor/statusline rendering. Adapt only the AMBIGUOUS_WIDE set after measuring YOUR host's glyph widths. Omit nothing — this is pure and fully tested.
