<!-- capsule-v2 -->
# Cache-friendly section formatting — why do stable sections come first, and how does the brief get capped without cutting a section in half?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What ordering makes the supervisor prompt prefix cacheable across analyses, and what is the exact line-cap re-cut rule?

## formatSummary (`src/compaction/format.ts`)
**Path/Symbol:** `src/compaction/format.ts:formatSummary` (:58-89), `capBrief` (:41-51), `wrapLine` (:12-33), `BRIEF_MAX_LINES=120`, `TUI_SAFE_LINE_CHARS=120`.
**Signature:** `(data: SectionData) => string` — empty data returns ''.
**Data Shape:** Stable sections: Session Goal, User Preferences, Files And Changes, Commits. Volatile: Type Catalog, Outstanding Context, Earlier Turns. Header block and brief transcript joined by `\n\n---\n\n`.

### Decisive source
```ts
// Cache-friendly ordering: stable first, volatile last
const stableSections = [goal, preferences, filesAndChanges, commits];
const volatileSections = [typeCatalog, outstandingContext, turnSummaries];
...
if (data.briefTranscript) parts.push(capBrief(data.briefTranscript));
const capBrief = (text) => {
  if (lines.length <= BRIEF_MAX_LINES) return text;
  const kept = lines.slice(-BRIEF_MAX_LINES);              // keep the LAST 120 (recent)
  const firstHeader = kept.findIndex(l => /^\[.+\]/.test(l)); // re-cut to first SECTION header
  const clean = firstHeader > 0 ? kept.slice(firstHeader) : kept;
  return `...(${omitted} earlier lines omitted)\n\n${clean.join('\n')}`;
};
// wrapLine: continuation indent mirrors bullet indent (≤8), split point must be ≥50% of width
```

**Flow:** sections render as `[Title]\n- item` blocks; stable block first so the token prefix (goal + prefs + files + commits — mostly unchanged between consecutive analyses) hits the provider's prompt cache; volatile content and then the transcript follow. The whole context is wrapped to 120-char lines with indent-preserving continuations.
**Invariant:** (1) Section ORDER is part of the contract — moving volatile sections forward defeats caching every analysis. (2) capBrief keeps the tail but NEVER opens with a partial section: re-cut to the next header, and the omission count is explicit. (3) Wrapping preserves list indentation so bracketed structure survives narrow terminals.
**Probe:** `tests/full-fidelity-snapshot.test.ts` formatForSupervisor suite — `formats sections as text` (:221), `includes relevant sections for steering decisions` (:229), `returns empty string when no data` (:244).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "formatSummary capBrief BRIEF_MAX_LINES stableSections", limit: 8 });
```

## Verdict
Adopt stable-first/volatile-last ordering + tail-capped-header-aligned brief for any repeatedly-built judge prompt. Adapt section titles/order within the stable/volatile split only. Omit TUI wrapping if your prompts go straight to an API.
