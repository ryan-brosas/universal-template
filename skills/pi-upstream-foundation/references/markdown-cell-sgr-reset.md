<!-- capsule-v2 -->
# Table-cell SGR reset — why do multi-line styled table cells bleed bold across rows?

**Source:** pi-upstream MIT `main@a470b121bf683b4c2b9fc0b3a7c807de7e0cfe9c` (drift commit `a470b121`-window change to markdown.ts). Codebase Memory `pi-upstream`. **Question:** A porter wraps styled text into fixed-width table cells and reuses the cell's style prefix per fragment — why does styling leak past the last fragment, and what must accompany each wrap?

## wrapCellText: reset after every non-final wrapped fragment, restore prefix before padding
**Path/Symbol:** `packages/tui/src/components/markdown.ts:829-837` (`private wrapCellText(text, maxWidth, stylePrefix = "")`), call sites :966 (header cells), :989 (body row cells) passing `styleContext?.stylePrefix`.
**Signature:** `wrapCellText(text: string, maxWidth: number, stylePrefix?: string): string[]` — delegates wrapping to `wrapTextWithAnsi(text, Math.max(1, maxWidth))`, then post-processes lines.
**Data Shape:** Input is pre-rendered ANSI text; output is one array element per visual line, each already carrying trailing control sequences so the table painter can pad + add borders without knowing about styles.

### Decisive source
```ts
private wrapCellText(text: string, maxWidth: number, stylePrefix = ""): string[] {
    const lines = wrapTextWithAnsi(text, Math.max(1, maxWidth));
    return lines.map((line, index) => {
        // Reset text styles after each non-final fragment, then restore the surrounding style before padding and borders.
        const styleReset = index < lines.length - 1 ? "\x1b[22;23;24;25;27;28;29;39m" : "";
        return `${line}${styleReset}${stylePrefix}`;
    });
}
```

**Flow:** renderInlineTokens produces styled text → wrapTextWithAnsi splits at width → for each fragment EXCEPT the last, append the SGR reset string `\x1b[22;23;24;25;27;28;29;39m` (clears bold/italic/underline/strikethrough/reverse/conceal/foreground intensity) → then append the surrounding `stylePrefix` so padding and border glyphs inherit the CELL's style, not a dangling inner style.
**Invariant:** Wrapping styled text cannot be style-neutral: every interior fragment boundary needs an explicit reset because SGR states persist across line breaks, and every fragment (including the last) needs the enclosing prefix re-appended because the wrapper's output will be padded/bordered by code that assumes clean state. The reset uses the 22-29 range (attribute clears), NOT `\x1b[0m`, precisely to preserve the surrounding cell style while killing inline emphasis.
**Probe:** Deterministic source probes from repo root at this pin: `grep -cF '\x1b[22;23;24;25;27;28;29;39m' packages/tui/src/components/markdown.ts` (≥1) and `grep -n "wrapCellText(text, columnWidths\[i\], styleContext?.stylePrefix)" packages/tui/src/components/markdown.ts` (2 hits: header :966 + body :989). Coverage caveat: no dedicated upstream unit test pins the reset sequence at this pin — markdown.test.ts covers wrapping generally.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "wrapCellText stylePrefix wrapTextWithAnsi", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-fragment attribute-clear resets (22-29 range, not full 0-reset) plus enclosing-prefix restoration on every wrapped styled fragment that later undergoes padding or bordering. Adapt the exact SGR bytes to your renderer's attribute set. Omit if your cells are never styled or never wrapped. Coverage caveat: pinned by source citation + live greps only; no direct unit test of the reset bytes upstream at this pin.
