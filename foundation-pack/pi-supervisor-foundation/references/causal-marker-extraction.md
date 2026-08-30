<!-- capsule-v2 -->
# Causal marker extraction — marker-scan cause/resolution fragments with bounded sentinels and breadcrumb keys

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you pull cause→fix pairs out of assistant prose deterministically, without regex backtracking risk?

## Marker lists + bounded fragment scan
**Path/Symbol:** `src/compaction/brief.ts:521-684` (`CAUSE_MARKERS` :521, `RESOLUTION_MARKERS` :566, `extractFragment` :633, `extractCausalChain` :661), key refinement `src/compaction/causal-keys.ts:129-138`.
**Signature:** `extractCausalChain(text): { cause: string|null; resolution: string|null }`; caps `FRAGMENT_MAX = 60`, `CAUSAL_BREADCRUMB_MAX = 40`, `KEY_MAX_WORDS = 3`.
**Data Shape:** ~40 cause markers ordered most-specific-first (`the issue is` … `because `, `stale `, `unhandled `); ~50 resolution markers (`fix this by` … `by adding`, `removed `).

### Decisive source
```ts
const extractFragment = (text: string, markers: readonly string[]): string | null => {
  const lower = text.toLowerCase();
  for (const marker of markers) {
    const idx = lower.indexOf(marker);
    if (idx < 0) continue;
    const start = idx + marker.length;
    ...
    while (end < text.length && end - start < FRAGMENT_MAX) {
      if (SENTINEL_CHARS.has(text[end])) break;   // ... , . ; ! ? \n
      end++;
    }
    const fragment = text.slice(start, end).trim();
    if (fragment.length < 4) continue;
    return fragment;
  }
  return null;
};
```
Per-sentence fallback (:671-678): when full-text scan misses one side, split on `[.!?]` and retry per sentence — handles cause and resolution living in different sentences. Breadcrumb key = file (last-2-path-segments) + stopword-refined resolution key joined `file|key`.

**Flow:** turn flush → join assistant texts → extract cause+resolution → synthesize one-line turn summary `user-text → cause → resolution → actions` → breadcrumb key for the recall system.
**Invariant:** The in-source design note (:511-517) is the contract: indexOf + linear scan is O(n) worst case, bounded by construction via FRAGMENT_MAX, extensible by appending strings — do NOT "simplify" to lazy-quantifier regexes. Fragments under 4 chars are rejected as noise. Same text always yields the same chain (deterministic for cache-friendly summaries).
**Probe:** `grep -c "FRAGMENT_MAX = 60" src/compaction/brief.ts` → 1; `grep -cn "'because '" src/compaction/brief.ts` → 1; `grep -c "KEY_STOPS.has\|KEY_MAX_WORDS = 3" src/compaction/causal-keys.ts` → 2. Direct-test caveat: causal extraction has no dedicated upstream describe block — pinned by source read; turn summaries exercised indirectly via `tests/full-fidelity-snapshot.test.ts` buildCompactionSummary suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "buildBriefSections|collapseSkillText|identifyTurns", limit: 10 });
```

## Verdict
Adopt marker-based causal extraction wherever LLM-free summarization must answer "why did it get stuck / what fixed it". Adapt both marker lists to your domain language (they are data, not logic). Omit the sentence-split fallback only if your inputs are single-sentence by construction.
