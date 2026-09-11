<!-- capsule-v2 -->
# Formatting-aware whitespace mode — how do you ignore pure-reflow and import-only changes in a diff while keeping hunk staging byte-exact?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What is the three-mode whitespace ladder, and under what exact conditions is a changed block demoted to context?

## Demotion predicate
**Path/Symbol:** `packages/coding-agent/src/cli/git-tui/diff-pane.ts:` `WhitespaceMode` (:20–28), `IMPORT_LANG_BY_EXT` (:31–41), `IMPORT_LINES` grammar (:44–62), demotion inside `buildDiffDocument` (:184–411, `demoteBlock` + import gate :255–280); tests `packages/coding-agent/test/git-tui-stream.test.ts:202-291`.
**Signature:** `buildDiffDocument(oldText, newText, filePath, options?: { whitespace?: "off" | "whitespace" | "formatting" })`.
**Data Shape:** Per-language `{starter, continuation, removable}` regex triple for ts/rust/go; demotion = changed block rendered as context rows (one-sided demoted rows keep their NEW-side line numbers for the gutter).

### Decisive source
```ts
const demoteBlock = (dels: number[], adds: number[]): boolean => {
	if (!ignoreFormatting) return false;
	const stripBlock = (lines, indices, removable) => {
		let out = "";
		for (const idx of indices) {
			const raw = lines[idx] ?? "";
			if (removable?.test(raw.trim())) continue;      // self-contained imports dropped first
			out += raw.replace(/\s+/g, "");                 // then compare whitespace-stripped text
		}
		return out;
	};
	if (stripBlock(oldLines, dels, null) === stripBlock(newLines, adds, null)) return true;   // pure reflow
	if (!importLang) return false;
	// import-only: every changed line matches starter|continuation AND ≥1 starter:
	for (...) { if (starter.test(line)) sawImport = true; else if (!continuation.test(line)) return false; }
	return sawImport;
};
```

**Flow:** mode `off` = byte-exact default; `whitespace` aligns ignoring leading/trailing ws but DISABLES hunk patches (`canPatch:false`) because alignment no longer matches git's view; `formatting` keeps exact alignment and instead DEMOTES changed blocks that are (a) whitespace-only movement (strip-all-whitespace equality) or (b) import-statement-only per language grammar — mixed blocks (import + real change) stay changed. A fused import-add + reflow demotes only after removable self-contained imports are stripped and the remainder compares equal.
**Invariant:** Formatting mode never breaks staging: hunks/patches still reconstruct against the REAL base — `"selection patches reconstruct the base across demoted one-sided rows"` pins patch content containing the original ` foo(a, b)` context line, i.e. demoted rows must mirror the OLD side, never leak empty lines. Language gating is by extension (`fixture.py` keeps its import addition counted). Import recognition requires ≥1 starter line so a bare comment or closing brace alone cannot demote.
**Probe:** `test/git-tui-stream.test.ts` — `"keeps blocks that change more than whitespace"` (deletions 1 / additions 4), `"demotes rust use reordering across separate blocks"`, `"import demotion is language-gated"`, `"keeps hunk patches, unlike whitespace mode"` (`canPatch true` vs false) — all line-pinned at :207–272.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "buildDiffDocument whitespace formatting demote", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `buildDiffDocument diff-pane.ts:184-411`.

## Verdict
Adopt the three-mode ladder for review UIs where reformat noise drowns real changes; keep formatting-mode's canPatch:true advantage over naive ignore-ws. Adapt the import grammars to your languages (the triple shape generalizes); preserve old-side mirroring for demoted rows or staged patches corrupt. Omit go/ts specifics you don't need — but keep SOME starter-required gate.
