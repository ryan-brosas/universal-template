<!-- capsule-v2 -->
# Spec-stats stat-race tolerance — how should a test runner treat a file that vanishes while its size is being collected, and what is the stats cache even for?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b3`); Codebase Memory `vitest`. **Question:** What happens when `stat` fails during spec-size collection, and why is swallowing the error correct here?

## Best-effort size census with in-flight-delete tolerance
**Path/Symbol:** `packages/vitest/src/node/cache/files.ts:FilesStatsCache.updateStats` (:23–32, post-#11023 form), `populateStats` (:15–21), `removeStats` (:34–40).
**Signature:** `public async updateStats(fsPath: string, key: string): Promise<void>`; key format `${spec.project.name}:${relative(root, spec.moduleId)}`.
**Data Shape:** `Map<string, { size: number }>` keyed by project-qualified relative path. Consumers use it ONLY as a sequencing heuristic — the shard/sort layer orders files by descending size to surface failures earlier; a missing entry degrades ordering, never correctness.

### Decisive source
```ts
public async updateStats(fsPath: string, key: string): Promise<void> {
  try {
    const stats = await fs.promises.stat(fsPath)
    this.cache.set(key, { size: stats.size })
  }
  catch {
    // the file can be deleted while the stat is in flight; a file
    // without stats only loses sorting heuristics
  }
}
```

**Flow:** `populateStats` fires all specs' `updateStats` concurrently (`Promise.all`) → each stat is independent → deletion between listing and stat lands in the catch → no entry written → downstream sorting treats the file as size-less and still runs it. Pre-#11023 form was existsSync-then-stat (TOCTOU race: the file could vanish between the two calls anyway).
**Invariant:** The stats cache is ADVISORY ONLY (sorting heuristic); absence of an entry must never fail or skip a test file. Swallowing here is deliberate — contrast with the same repo's cache-integrity code where metadata write failures are logged but lockfile mismatches act. A porter who propagates this error turns a cosmetic watch-mode delete into a failed run; one who pre-checks with existsSync keeps a TOCTOU window instead.
**Probe:** `sed -n '28,31p' packages/vitest/src/node/cache/files.ts` shows the exact catch comment ("the file can be deleted while the stat is in flight"); `grep -c 'removeStats' packages/vitest/src/node/cache/files.ts` = 1 (def :34; callers invalidate by suffix match). Verified on disk at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "FilesStatsCache updateStats populateStats getStats", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt advisory-only stats collection with silent per-file failure for any host that orders work by file metrics. Adapt the key scheme to your host's identity model. Omit nothing — the whole seam is three methods; the porting question is exactly which consumers may treat absence as "no data" versus "broken".
