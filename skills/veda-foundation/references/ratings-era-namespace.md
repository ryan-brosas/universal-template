<!-- capsule-v2 -->
# Ratings-era namespace — how does a Glicko-2 snapshot store apply one rating period atomically without reentrant locking, and never fail its caller?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** How do you persist per-entity rating states keyed by an evolving catalog namespace, updating them atomically per run under a non-reentrant lock, with best-effort semantics that can never crash the pipeline?

## Connected graph-selected seam
**Path/Symbol:** `src/stats/ratings-store.ts:RatingsStore` (:27–164) — public `load`/`loadCurrentEra`/`save`/`applyRatingPeriod`/`getByPrefix`, private `loadUnlocked`/`saveUnlocked`/`namespaceMatchesByEra`; sole caller is `PairwiseStatsStore.append` (trace_path inbound, depth 2).
**Signature:** `applyRatingPeriod(entry: AnyPairwiseStatEntry): Promise<void>`; `getByPrefix(prefix: string, eraSelector: string = 'current'): Promise<Map<string, RatingState>>`.
**Data Shape:** `RatingsSnapshotV2 = { version: 2, updatedAt: ISO, currentEra: EraRef, entities: Record<"<base>@m_xxxxxxxxxxxx", RatingState> }`; `RatingState = { r:1500, rd:350, vol:0.06, games, lastTs? }`.

### Decisive source
```ts
async applyRatingPeriod(entry: AnyPairwiseStatEntry): Promise<void> {
  try {
    await withLock(this.path, async () => {
      const current = await this.loadUnlocked();          // NOT this.load() — lock held
      const { judges, models, modules, categories } = deriveAllMatches(entry);
      const allMatches = mergeMatches(judges, models, modules, categories);
      const namespacedMatches = this.namespaceMatchesByEra(allMatches, entry);
      const updated = glicko2UpdatePool(current, namespacedMatches);
      await this.saveUnlocked(updated);                   // NOT this.save()
    });
  } catch {
    // Best-effort: don't fail the pipeline
  }
}
private namespaceMatchesByEra(matches, entry) {
  if (entry.version === 1) return matches;                // legacy keys stay unsuffixed
  const eraId = entry.era.id;
  /* suffix every key AND opponentKey with `@${eraId}` */
}
```

**Flow:** one pairwise vote-entry = one rating period → derive matches across four entity ladders (judges/models/modules/categories) → era-suffix every key (v2 only; v1 entries pass through unsuffixed forever) → Glicko-2 pool update → rewrite whole snapshot under the lock.
**Invariant:** header contract *"Persistent Glicko-2 ratings snapshot. Never throws (best-effort)."* — `load` returns empty Map on missing file/version≠1&&≠2/parse error; `applyRatingPeriod` swallows everything; reads inside a held lock must use the *Unlocked variants because `withLock` deadlocks on reentry; `save` stamps `currentEra: getCurrentEra()` so the file self-describes its namespace; `getByPrefix` understands exactly four selectors: `'all'`, `'legacy'` (unsuffixed keys), `'current'` (key era === live digest id), or an explicit era id.
**Probe:** no dedicated upstream test for `RatingsStore` (verified by targeted grep over `tests/`). Source-pinned deterministic probe: the version-gate line `if (snapshot.version !== 1 && snapshot.version !== 2) return new Map();` appears identically in `load` (:40) and `loadUnlocked` (:146), and `tests/stats/store.test.ts` pins the sibling store's equivalent lenient-read behavior live (7 pass / 0 fail executed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "RatingsStore applyRatingPeriod loadCurrentEra namespaceMatchesByEra getByPrefix", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: era-suffixed entity keys inside a versioned snapshot that records its own `currentEra`, atomic read-modify-write via unlocked internals under one external lock, and total best-effort error swallowing. Adapt the rating math (plug your own estimator behind `glicko2UpdatePool`) and the four-ladder match derivation. Omit nothing structural. Caveats: no upstream direct test; and note the deliberate asymmetry that legacy v1 data is readable via `'legacy'` selector but never migrated into v2 namespaces.
