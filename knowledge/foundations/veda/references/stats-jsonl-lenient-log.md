<!-- capsule-v2 -->
# Lenient JSONL stats log — how do you append telemetry that survives corrupted lines, future schemas, and concurrent writers without ever failing a run?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** How should an append-only JSONL event log behave on read when lines are malformed, versions are unknown, or old entries lack newer required fields?

## Connected graph-selected seam
**Path/Symbol:** `src/stats/store.ts:StatsStore` (:18–153) and `src/stats/pairwise-store.ts:PairwiseStatsStore` (:17–86) — two JSONL logs over the same pattern; direct test `tests/stats/store.test.ts` pins the read ladder.
**Signature:** `append(entry): Promise<void>`; `readAll(): Promise<AnyStatEntry[]>`; `count(): Promise<number>`; pairwise adds `countByEra(eraId | 'legacy')`; stats adds `getRunIds()` / `getModuleWinRates()` (v3-only aggregation).
**Data Shape:** one JSON object per line; `version: 1|2|3` discriminator (stats) or `1|2` + `judgeMode:'pairwise'` + optional `era: EraRef` (pairwise).

### Decisive source
```ts
for (const line of content.split('\n')) {
  if (!line.trim()) continue;
  try {
    const parsed = JSON.parse(line);
    if (parsed.version === 1 || parsed.version === 2) {
      if (parsed.version === 1 && !parsed.judgeMode) parsed.judgeMode = 'single'; // normalize-on-read
      entries.push(parsed as StatEntry);
    } else if (parsed.version === 3) {
      entries.push(parsed as StatEntryV3);
    }                      // unknown versions silently dropped
  } catch { /* Skip malformed lines */ }
}
```

**Flow:** append = `withLock(path)` → mkdir parent → read whole existing text → rewrite `existing + JSON.stringify(entry) + '\n'`; readAll = split lines → skip blanks → per-line try/parse → version-gate → normalize old schemas on read.
**Invariant:** reads never throw and never include invalid data — malformed lines and unknown versions are *skipped*, not fatal and not preserved; v1 entries gain `judgeMode:'single'` at read time so downstream code sees one schema; both stores swallow all errors ("best-effort recording"). Honest caveat: "append" is a **locked whole-file rewrite**, safe against interleaving but O(n) per append — do not port assuming O(1) fs.appendFile semantics. Pairwise `readAll` additionally filters `judgeMode === 'pairwise'` so the two logs can share format conventions without cross-polluting.
**Probe:** `tests/stats/store.test.ts` executed live at pin: **7 pass / 0 fail** — includes `readAll skips malformed lines` (manual `{ invalid json }` injection), `readAll skips entries with unknown version` (`version: 99`), and `preserves all fields in roundtrip` pinning the `judgeMode:'single'` normalization via exact `toEqual`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "StatsStore append readAll judgeMode skip malformed jsonl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lenient-read ladder (skip-don't-fail, version-gate, normalize-on-read) for any agent-run telemetry log. Adapt storage to true appends + a file lock if volumes grow, keep the version discriminator per line so mixed-era files stay readable, and preserve the invariant that a corrupt line degrades to nothing while its neighbors survive.
