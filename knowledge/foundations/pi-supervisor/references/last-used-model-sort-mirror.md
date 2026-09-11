<!-- capsule-v2 -->
# Last-used model sort mirror — mirroring another extension's persisted usage order inside your own picker

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you make your custom picker match the ordering of a host picker that another extension monkey-patches, without depending on that extension?

## Read their data file, re-apply their algorithm
**Path/Symbol:** `src/ui/model-sort.ts:28-101` (config path :28, `buildModelKey` :36, `readModelSortLastUsed` :45, `hasUsageData` :61, `sortByLastUsed` :77); consumers in `src/ui/model-settings-selector.ts:239-253` (`sortModels`) and :289-315 (`filterModels`).
**Signature:** `sortByLastUsed<T extends {provider,id}>(items, lastUsed: LastUsedMap, currentModelKey: string | null): T[]` — non-mutating copy-sort.
**Data Shape:** Config `~/.pi/agent/extensions/pi-model-sort.json` shape `{ lastUsed: { "provider/id": timestampMs } }`.

### Decisive source
```ts
 * Mirrors pi-model-sort's sortByLastUsed algorithm exactly:
 *   1. Current model first (if currentModelKey is provided)
 *   2. Most recently used (highest timestamp) first
 *   3. Provider name alphabetically
 *   4. Model id alphabetically
```
```ts
    if (currentModelKey !== null) {
      const aIsCurrent = aKey === currentModelKey; ...
    }
    const aLast = lastUsed[aKey] ?? 0;   // no usage ⇒ 0 ⇒ sorted last
    if (aLast !== bLast) return bLast - aLast;
    return a.provider.localeCompare(b.provider) || a.id.localeCompare(b.id);
```
Filter re-application (selector :296-311): after fuzzy filtering REORDERS by match quality, the last-used sort is applied AGAIN when >1 result — so typing doesn't discard usage order — and the cursor is re-synced onto the current model.

**Flow:** selector construction reads pi-model-sort's file once → usage data present? sortModels mirrors it : provider-default sort → search filters then re-applies usage sort → selection never writes global default ("Unlike pi-core, do NOT write the user's global default model" :432-433).
**Invariant:** The mirror is read-ONLY toward the other extension's data (sharing the file keeps both pickers in sync without write contention). Missing/unreadable config degrades to provider sort via typed guard `hasUsageData` (null/empty ⇒ false). The four-level comparator order is the compatibility contract with the patched host picker.
**Probe:** `grep -c "MODEL_SORT_CONFIG_PATH" src/ui/model-sort.ts` → 3. Direct tests: `tests/model-sort.test.ts:24/:36/:50/:83` describe blocks buildModelKey / hasUsageData / readModelSortLastUsed / sortByLastUsed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "buildModelKey|sortByLastUsed|readModelSortLastUsed", limit: 10 });
```

## Verdict
Adopt cooperative mirroring (read sibling extensions' persisted state + replicate their comparator) for UX parity without runtime coupling. Adapt the config path/comparator to whatever you mirror. Omit nothing on degradation guards — absent-file must equal absent-feature, never error.
