<!-- capsule-v2 -->
# Progressive-tier status line — how do you render a two-zone (left preserved / right compressed) footer that always fits exactly?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** How do you build a status line whose left side keeps full fidelity while the right side degrades through pre-built tiers as the terminal narrows — never overflowing, never leaving a ragged edge?

## buildAccountTiers + StatusLineWidget.render
**Path/Symbol:** `status.ts:159-202` (`buildAccountTiers` :159-201, tier ladder), `status.ts:282-318` (`StatusLineWidget` incl. `render`), session side `status.ts:146-149` (`buildSessionLine`), formatters `status.ts:114-144` (`formatBalHc`/`formatSpendHc`/`formatRateCompact`). DIRECT TESTS: `tests/status.smoke.ts:79-136` (width tiers + widget render + crash guard).
**Signature:** `buildAccountTiers(acc: AccountState, lowBalance: boolean): string[]`; `new StatusLineWidget(theme: LineTheme, leftRaw: string, rightTiers: string[] = [], rightWarn = false)`; `render(width: number): string[]`.
**Data Shape:** tiers = ordered most→least detailed strings, adjacent duplicates removed; atoms joined `" · "`, team+gem joined by space as one identity unit.

### Decisive source
```ts
render(width: number): string[] {
	const leftVis = termVisWidth(this.leftRaw);
	if (leftVis > width) {
		return [this.theme.fg("dim", truncateAnsi(this.leftRaw, width))];
	}
	const rightColor = this.rightWarn ? "warning" : "dim";
	const themedLeft = this.theme.fg("dim", this.leftRaw);
	const budget = width - leftVis - 1;
	for (const tier of this.rightTiers) {
		if (termVisWidth(tier) <= budget) {
			const themedRight = this.theme.fg(rightColor, tier);
			const pad = width - termVisWidth(themedLeft) - termVisWidth(themedRight);
			return [themedLeft + " ".repeat(Math.max(1, pad)) + themedRight];
		}
	}
	return [themedLeft + " ".repeat(Math.max(0, pad))];   // no tier fits → left only
}
```

**Flow:** measure left → if left alone overflows, truncate it (crash guard) → else budget = width − leftVis − 1 → first fitting tier wins → justify with padding to EXACTLY width → fallback left-only padded.
**Invariant:** the rendered line is ALWAYS exactly `width` visible columns (smoke asserts `termVisWidth(render(80)[0]) === 80`, and for 52, narrow, tiny widths too). Left is verbatim-preserved; compression order drops auth days FIRST, then day rate, then team identity (`tiers` array order at `:162-171`). Empty-left sessions right-align account-only. Warning state flips BOTH the gem glyph (⚠ ◆) and the theme color. Tiers are strictly non-increasing in width (asserted loop `:59-61`) and deduped when atoms are missing.
**Probe:** `tests/status.smoke.ts:79-121` — wide/medium/narrow/tiny renders, right-only alignment, empty-data line, warning color wired through both a fake ANSI theme and a marker theme. GREEN on Node 26.7.0.
**Coverage caveat:** none — direct test exists.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "StatusLineWidget", limit: 5 });
// → pi-hypercharm-provider.StatusLineWidget Class status.ts
```

## Verdict
Adopt the widget + tier builder wholesale for any width-constrained two-zone line. Adapt atom composition/glyphs to your data. Omit nothing in the layout math — it is fully test-pinned.
