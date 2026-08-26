<!-- capsule-v2 -->
# Co-change history as recency-decayed seed overlay — why git co-edit affinity must never become a permanent graph edge?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Files that always move together share no static edge — how do you inject that history signal without pinning stale coupling into the structure forever?

## History rides beside the graph; recency applied at USE time
**Path/Symbol:** `src/core/cochange.ts:coChangeHistory/scorePair/recencyFactor/effectiveWeight` (:31-188); consumer `src/core/ops.ts:historySeedWeights` (:580-600) + impact overlay (:951-964, :1054-1064).
**Signature:** `coChangeHistory(root, filesInGraph, now): Promise<Map<file, CoChangePartner[]>>` where partner `{partner, w, lastTs}`; `recencyFactor(ageDays) = 2^(-ageDays/COCHANGE_HALF_LIFE_DAYS)` (30d default, `FOVEA_COCHANGE_HALF_LIFE_DAYS`); `scorePair(n, soloA, soloB) = min(0.5, 0.08 + 0.55·jaccard + 0.10·min(n/10,1))`.
**Data Shape:** Mined from `git log --format=%x00%ct --numstat -n 400 --no-renames --diff-filter=AMR`: commits with <2 or >24 tracked files carry no pair signal; pairs need ≥2 joint commits (`MIN_SHARED=2`); each file keeps its top-16 partners ranked by EFFECTIVE (already-decayed) hotness. Cache keyed by HEAD + sorted tracked-set hash (`v:2`).

### Decisive source
```ts
// Under the all-in heat model that signal is a seeded field, not permanent
// structure. w = w0(count, jaccard) * 2^(-ageDays / COCHANGE_HALF_LIFE_DAYS)
// ... Nothing pins history into the graph, so old co-work cools out of the
// field exactly like every other heat source.
export const historySeedWeights = (seedFiles, graph, history, now): Map<string, number> => {
  const add = (file: string, w: number): void => {
    if (seedFiles.has(file)) return;               // never re-seed the change site
    partners.set(file, Math.max(partners.get(file) ?? 0, w));
  };
  for (const p of history.get(file) ?? []) {
    const ageDays = Math.max(0, (now - p.lastTs) / 86_400_000);
    const w = effectiveWeight(p.w, ageDays);
    if (w <= 1e-6) continue;                        // ancient joints drop out
    add(p.partner, w);
  }
};
```

**Flow:** mine raw facts (count + newest committer ts per pair) once per HEAD+tracked-set, CACHE THE RAW FACTS ONLY — then at every use, seed partner FILE NODES into the SAME diffusion as the changed files at min(baseW·decay) weight ("linearity makes this exactly heat(seeds + partners·w): ONE cascade"). Impact labels those files' reasons with `"co-change history"` (string must equal sync's CHANNEL_WEIGHT key so the surprise gate weighs it identically to the old edge era).
**Invariant:** Raw facts are cached by HEAD+tracked set but recency decays with the WALL CLOCK at use time — even a cache hit cools as time advances. History is NOT structure: focus/sketch stay pure structure; only impact re-seeds partners when a change lands. A fresh-but-weak pair outranks an ancient strong one in the keeper filter.
**Probe:** `tests/cochange.test.ts` — "recency decays exponentially to a half-life and ~0 when ancient" (40 half-lives < 1e-12; negative age never amplifies); "records the newest joint commit time and separates recent from stale" (real dated git commits, wC > wB·5); "historySeedWeights re-seeds only non-seed partners, recency-gated"; impact overlay test labels server/main.go "co-change history".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "coChangeHistory recencyFactor scorePair", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: Jaccard-tilted count-compressed pair scoring, commit-size gates, per-file top-k keeper by effective hotness, raw-fact caching + use-time decay, and seeding into the same diffusion instead of adding edges. Adapt window sizes (400 commits / 24-file cap / 16 partners) to repo scale. Omit nothing — the "history ≠ structure" invariant is the whole design.
