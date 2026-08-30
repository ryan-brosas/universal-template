<!-- capsule-v2 -->
# Model selection + last-used sort mirroring — how does a secondary picker match the user's primary picker ordering?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What exact sort key order reproduces pi-model-sort's ordering, and how is its config shared without coupling?

## sortByLastUsed + global config (`src/ui/model-sort.ts`, `src/global-config.ts`)
**Path/Symbol:** `model-sort.ts:sortByLastUsed` (:77-101), `readModelSortLastUsed` (:45-55), `buildModelKey` (:36-38); `global-config.ts:loadGlobalModel/saveGlobalModel` (:24-65).
**Signature:** `sortByLastUsed<T extends {provider,id}>(items, lastUsed: Record<"provider/id", ms>, currentModelKey): T[]` (non-mutating).
**Data Shape:** Shared file `~/.pi/agent/extensions/pi-model-sort.json` under key `lastUsed`; supervisor's own config `<cwd>/.pi/supervisor-config.json` key `model{provider,modelId}`.

### Decisive source
```ts
// Mirrors pi-model-sort's sortByLastUsed algorithm exactly:
// 1. Current model first  2. most-recent timestamp first
// 3. provider alphabetical 4. model id alphabetical; unused = timestamp 0 = last.
sorted.sort((a, b) => {
  if (currentModelKey !== null) { /* current-first short-circuit */ }
  const aLast = lastUsed[aKey] ?? 0, bLast = lastUsed[bKey] ?? 0;
  if (aLast !== bLast) return bLast - aLast;
  return a.provider.localeCompare(b.provider) || a.id.localeCompare(b.id);
});
// Config merge preserves foreign keys:
const merged = { ...existing, model };   // other keys in supervisor-config.json survive
```

**Flow:** `/supervise model` pre-highlights via precedence active-state > global config > chat model → picker sorts by mirrored last-used map (graceful null ⇒ default provider sort when the sibling extension isn't installed or JSON is corrupt) → save writes supervisor-config.json MERGING with existing keys and creating `.pi/` on demand. Model keys keep slashes (`openrouter/anthropic/claude...`) — no splitting on '/'.
**Invariant:** (1) Reading ANOTHER extension's datafile (not an API) is deliberate sharing — both pickers stay in sync for free; corruption degrades to null, never throws. (2) The four-level comparator is total: current-flag → recency → provider → id, so ordering is deterministic even with zero usage data. (3) Save merges rather than replaces — a porter clobbering unknown keys breaks sibling tools.
**Probe:** `tests/model-sort.test.ts` — `puts the current model first, ahead of more-recent models` (:110), `falls back to provider/id alphabetical for equal or missing timestamps` (:119), `does not mutate the input array` (:145); `tests/global-config.test.ts` `saveGlobalModel preserves other keys already present` (:42), `returns null when the model field is incomplete` (:66).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "sortByLastUsed readModelSortLastUsed saveGlobalModel merged", limit: 8 });
```

## Verdict
Adopt the 4-key comparator + read-sibling-config-with-null-fallback + merge-preserving save for any model/tool picker ecosystem. Adapt file paths. Omit current-first only if your UI has no pre-highlight concept.
