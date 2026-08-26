<!-- capsule-v2 -->
# Cache-friendly formatting — stable-before-volatile section ordering, tail-capped transcript with header-boundary snap

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How should a rebuilt-fresh-every-time summary be laid out so provider prompt caches still hit?

## Two-band section ordering
**Path/Symbol:** `src/compaction/format.ts:53-89` (`formatSummary`), `capBrief` :41-51, line wrapping :12-39.
**Signature:** `formatSummary(data: SectionData): string`; constants `BRIEF_MAX_LINES = 120`, `TUI_SAFE_LINE_CHARS = 120`.
**Data Shape:** Stable band = [Session Goal, User Preferences, Files And Changes, Commits]; volatile band = [Type Catalog, Outstanding Context, Earlier Turns]; then the brief transcript.

### Decisive source
```ts
export const formatSummary = (data: SectionData): string => {
  // Cache-friendly ordering: stable first, volatile last
  const stableSections = [
    section('Session Goal', data.sessionGoal),
    section('User Preferences', data.userPreferences),
    section('Files And Changes', data.filesAndChanges),
    section('Commits', data.commits),
  ].filter(Boolean);
```
capBrief keeps the LAST 120 lines and snaps the cut to a section header:
```ts
  const kept = lines.slice(-BRIEF_MAX_LINES);
  // Find first section header to avoid cutting mid-section
  const firstHeader = kept.findIndex((l) => /^\[.+\]/.test(l));
  const clean = firstHeader > 0 ? kept.slice(firstHeader) : kept;
  const crumbLine = `...(${omitted} earlier lines omitted)`;
```

**Flow:** sections render as `[Title]\n- item` blocks → stable band, volatile band, transcript → joined with `\n\n---\n\n` → every line hard-wrapped at 120 chars with hanging-indent continuation (list-aware).
**Invariant:** The summary is REBUILT from scratch on every analysis (no merge state — index.ts header comment: "One-shot, no merge, no state"); cacheability comes purely from putting low-churn content in the prefix. capBrief must never open mid-section: snapping to the next `[header]` guarantees the visible transcript starts at a semantic boundary, with an explicit omission count.
**Probe:** `grep -c "BRIEF_MAX_LINES = 120" src/compaction/format.ts` → 1. Direct test: `tests/full-fidelity-snapshot.test.ts:220` describe('formatForSupervisor').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "extractCommits|formatSummary|capBrief", limit: 10 });
```

## Verdict
Adopt stability-banded ordering for any frequently-regenerated prompt payload; adapt band membership to your churn profile. Keep header-snapped truncation — mid-section cuts read as corruption to the consuming model. Omit TUI wrapping if your consumer is not a terminal renderer.
