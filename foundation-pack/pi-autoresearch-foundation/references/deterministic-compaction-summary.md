<!-- capsule-v2 -->
# Deterministic compaction summary — why does compaction skip the LLM and rebuild from disk?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What replaces the default LLM-generated context summary, and what must it preserve for a memoryless agent?

## buildAutoresearchCompactionSummary — six synthesized sections replace conversation history
**Path/Symbol:** `extensions/pi-autoresearch/src/compaction/index.ts:41–54` (builder), wired at `extensions/pi-autoresearch/index.ts` `session_before_compact` :1057–1074 returning `{ compaction: { summary, firstKeptEntryId, tokensBefore } }`.
**Signature:** `buildAutoresearchCompansionSummary(paths: AutoresearchSummaryPaths, state: ExperimentState): string` — sections: header → session → rules → ideas → recentRuns → nextStep.
**Data Shape:** reads `autoresearch.md` + `autoresearch.ideas.md` whole; recent runs = `state.results.slice(-RECENT_RUN_LIMIT=50)`.

### Decisive source
```ts
// header section declares the contract outright:
'# Autoresearch Compaction Summary',
'The conversation history was discarded; the persisted autoresearch state below is the source of truth.',
'Continue the experiment loop using only what is included here plus the live tools.',
// per-run line format (documented IN the summary):
'Format: `#run status metric (delta) | desc | hyp: ... | next: ... | rollback: ...`',
```

**Flow:** pi fires `session_before_compact` → extension intercepts and returns a SYNTHETIC summary instead of letting an LLM summarize the dying context: goal/metric/status-counts of the CURRENT segment (`currentSegmentRuns` filter), baseline + best lines, verbatim rules file, verbatim ideas backlog, last 50 run lines with ASI fields surfaced as `hyp:/next:/rollback:` columns, closing instruction to pick the next hypothesis immediately. Delta computation uses the SEGMENT baseline even when it scrolled out of the 50-run window (`baselineFor` searches full results by segment — pinned by test 'uses segment baseline for delta computation').
**Invariant:** the summary is LOSSLESS ON WHAT COUNTS because everything that matters between iterations already lives in files — the LLM call is skipped entirely (cost + nondeterminism removed). The paired resume message (`composeCompactionResumeMessage`, index.ts :537–546) explicitly forbids re-reading the files the summary already embeds. Rules/ideas sections are omitted silently when files are absent (test-pinned).
**Probe:** direct test `__tests__/unit/compaction.test.ts` — six its pinning full-content assembly (:36–124), cold-start omissions (:126–149), post-reinit segment reflection (:151–201), 50-cap window boundaries #10/#11/#60 (:203–247), missing-files omission (:249–270), out-of-window baseline delta −5.1% (:272–315); anchor `grep -n 'RECENT_RUN_LIMIT' extensions/pi-autoresearch/src/compaction/index.ts` → :16 + :140.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "buildAutoresearchCompactionSummary session_before_compact RECENT_RUN_LIMIT", limit: 10 });
```

## Verdict
Adopt the deterministic-summary pattern verbatim for ANY long-lived agent loop (this is the repo's most transferable idea: compact into your persistence format, not prose); adapt section list/format to your domain; omit nothing structural. Fully direct-tested — the test file doubles as the porting spec.
