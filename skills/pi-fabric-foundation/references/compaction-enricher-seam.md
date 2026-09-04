<!-- capsule-v2 -->
# Compaction enricher seam — how do you let format-specific prose understanding extend a deterministic summarizer without touching its core?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** where does non-structural annotation plug in, and what does the core promise about it?

## Zero-builtin enricher interface, post-fold mutation
**Path/Symbol:** `src/compaction/enrichers.ts:CompactionEnricher` (:16-25), `NO_BUILTIN_ENRICHERS` (:29), `runEnrichers` (:31-40).
**Signature:** `{name: string; applies(events: CompactionEvent[]): boolean; contribute(events, sections): void}`; `runEnrichers(enrichers, events, sections): void` (in-place section mutation).
**Data Shape:** enrichers run ONCE per compaction, AFTER all structural sections are computed; the full event stream is re-available so an enricher derives its own state instead of re-walking raw logs differently from the core.

### Decisive source
```ts
// The core ships ZERO built-in enrichers on purpose: the redistilled core is
// the minimal clean baseline, and prose understanding is an additive concern
// an extension can register later without touching the projections.
export const NO_BUILTIN_ENRICHERS: readonly CompactionEnricher[] = Object.freeze([]);
...
for (const enricher of enrichers) {
  if (!enricher.applies(events)) continue;   // cheap skip before contribute
  enricher.contribute(events, sections);     // may append to or replace any section
}
```

**Flow:** core folds produce sections → registered enrichers filter via `applies` → each contributes in place (e.g. pulling a tsc line number out of a bash result, annotating a test-failure section) → serialization happens afterwards.
**Invariant:** determinism extends to extensions — "the same event stream must yield the same contribution, so the overall serialization stays byte-identical for a given input" (principle 5); the deterministic core NEVER inspects prose (principle 2): anything prose-understanding lives behind this interface. `applies` exists purely as a cheap gate; correctness must not depend on it.
**Probe:** consumer wiring pinned at `src/compaction/hook.ts` (`NO_BUILTIN_ENRICHERS` referenced :2 sites) and `src/compaction/branch-summary.ts`; no dedicated upstream test file for this 40-line seam — coverage caveat recorded here honestly (the interface's behavior is exercised transitively by every compaction end-to-end test).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "runEnrichers CompactionEnricher NO_BUILTIN_ENRICHERS applies contribute sections", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the empty-by-default enricher registry with applies/contribute split and the byte-determinism obligation on extensions; adapt section names and registration mechanics; omit nothing — the ZERO-builtin stance IS the design. No dedicated direct test file (consumer-tested caveat); graph coverage clean.
