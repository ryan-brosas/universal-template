<!-- capsule-v2 -->
# Causal chain + turn summaries (HCA zone) — how are cause→resolution pairs mined without an LLM?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do marker-based extractors stay O(n) and bounded, and how does a turn summary line become a recall key?

## identifyTurns + causal extraction (`src/compaction/brief.ts:501-833`, `src/compaction/causal-keys.ts`)
**Path/Symbol:** `src/compaction/brief.ts:extractFragment` (:633-651), `extractCausalChain` (:661-684), `synthesizeTurnSummary` (:693-731), `buildCausalBreadcrumb` (:740-764), `identifyTurns` (:777-833); `src/compaction/causal-keys.ts:refineBreadcrumbKey` (:129-138).
**Signature:** `(text, markers) => string|null`; `identifyTurns(blocks) => TurnInfo[]`.
**Data Shape:** CAUSE_MARKERS (~40 phrases, most→least specific) and RESOLUTION_MARKERS (~50); `FRAGMENT_MAX=60` chars, `CAUSAL_BREADCRUMB_MAX=40`, `KEY_MAX_WORDS=3`.

### Decisive source
```ts
// Why markers instead of regex? 1. No backtracking risk — indexOf + linear char scan is O(n).
// 2. Bounded by construction — FRAGMENT_MAX hard cap. 3. Easy to extend — add a string.
const extractFragment = (text, markers) => {
  const lower = text.toLowerCase();
  for (const marker of markers) {
    const idx = lower.indexOf(marker);
    if (idx < 0) continue;
    let end = start;
    while (end < text.length && end - start < FRAGMENT_MAX)
      { if (SENTINEL_CHARS.has(text[end])) break; end++; }   // ...,.!?;\n terminate
    const fragment = text.slice(start, end).trim();
    if (fragment.length < 4) continue;                        // too-short ⇒ try next marker
    return fragment;
  }
};
// Per-sentence fallback when full-text scan misses one side of the pair.
// Turn boundary: user OR bash block starts a new turn; flush() synthesizes
// "userText → cause → resolution → actions" joined with ' \u2192 '.
const resolutionKey = refineBreadcrumbKey(resolution);        // stop-word-stripped 3-word '-' join
if (file && resolutionKey) return `${file}|${resolutionKey}`; // breadcrumb format: file|key
```

**Flow:** turns accumulate assistant text until the next user/bash block → causal chain extracted from the JOINED assistant text (full-text first, then per-sentence for split pairs like "The issue is X. Fixed by adding Y.") → summary = clipped user text → cause → resolution → deduped actions (≤5; edit-heavy turns collapse others to "+N more") → breadcrumb built from shortened file path + refined resolution key.
**Invariant:** (1) Markers are ORDERED most-specific-first — first match wins, so "root cause:" beats bare "because ". (2) Fragments are hard-capped twice (60 raw / 40 key) — no unbounded capture exists anywhere in the pipeline. (3) Marker REMNANT verbs (added/created/implemented…) are in KEY_STOPS so keys read "session-check", not "added-session-check". (4) Empty fragments (<4 chars) fall through to the next marker rather than emitting junk.
**Probe:** constants pinned at brief.ts :621-626 (`FRAGMENT_MAX`, `CAUSAL_BREADCRUMB_MAX`, `SENTINEL_CHARS`) and causal-keys.ts :10/:123; turn grammar via `grep -c "kind === 'user' || b.kind === 'bash'" src/compaction/brief.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "extractCausalChain CAUSE_MARKERS refineBreadcrumbKey identifyTurns", limit: 8 });
```

## Verdict
Adopt marker-list causal mining with double caps and per-sentence fallback as the deterministic alternative to LLM summarization. Adapt marker phrasing to your domain's language. Omit breadcrumb file-prefixing if your summaries don't reference files.
