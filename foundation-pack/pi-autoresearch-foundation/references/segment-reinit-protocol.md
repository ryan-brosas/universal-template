<!-- capsule-v2 -->
# Segment protocol — how does re-initializing an experiment archive history without losing it?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What exactly resets on `init` over an existing JSONL, and how do UI surfaces stay segment-local while confidence stays global?

## currentSegment increment + resetForReinit — append a header, filter per surface
**Path/Symbol:** `harness/server.ts:init` :813–895 (isReinit :840, resetForReinit :324–331 called at :852); reconstruction sets `currentSegment = entry.segment ?? 0` (:669); consumers: `src/utils/experiment.ts:8–16` (`currentResults`, `findBaselineMetric`), widget/table filters (`r.segment !== state.currentSegment ⇒ skip`).
**Signature:** `resetForReinit(state, incrementSegment=true)`: `state.currentSegment++; state.bestMetric=null; state.secondaryMetrics=[]; state.confidence=null;`
**Data Shape:** every run row carries its `segment`; config headers also carry it; "current" = highest header seen.

### Decisive source
```ts
const isReinit = fs.existsSync(jsonlPath);
// ...
if (isReinit) resetForReinit(session.state, true);
// then APPENDS (never truncates):
fs.appendFileSync(jsonlPath, config + '\n');
```

**Flow:** second `init` in the same worktree → bump segment → null baseline/secondary/confidence → append new config header → next runs log with the NEW segment. Widget collapsed view and dashboard table iterate results but SKIP rows from other segments; compaction summary counts/baselines use `currentSegmentRuns`. Confidence deliberately does NOT segment-filter (pools all positive metrics for a stabler noise floor). Old rows remain on disk forever — the JSONL doubles as the archive.
**Invariant:** re-init never destroys data — the new baseline is just "first run of the newest segment", which is why `findBaselineSecondary` falls back to first occurrence of each metric WITHIN the segment when the baseline predates that metric's introduction. A porter who clears the file on re-init breaks the audit trail; one who forgets the segment filter shows stale-segment numbers as current.
**Probe:** direct tests `__tests__/unit/utils.test.ts:343–380` ('findBaselineMetric' incl. 'only considers specified segment') + `__tests__/unit/utils.test.ts:385–415` ('currentResults') + `__tests__/unit/compaction.test.ts:151–201` ('session block reflects current segment after re-init'); anchor `grep -n "entry.segment ?? 0" extensions/pi-autoresearch/index.ts | wc -l` → 2 (config + run branches of the reconstructor).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "resetForReinit currentSegment currentResults findBaselineMetric", limit: 10 });
```

## Verdict
Adopt the monotone-segment protocol verbatim (archive-by-header is cheaper and safer than any rotation scheme); adapt naming; omit nothing. Direct tests cover filtering, baselining, and post-reinit summary behavior.
