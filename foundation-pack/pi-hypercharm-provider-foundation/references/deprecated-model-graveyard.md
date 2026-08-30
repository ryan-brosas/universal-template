<!-- capsule-v2 -->
# Deprecated-model grace period — how do you delist a model without breaking in-flight sessions and saved settings?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** When the upstream catalog stops listing a model, how do you keep it working for a bounded window (and resurrect it if it returns) instead of hard-dropping it?

## updateDeprecatedModels graveyard + runtime replay
**Path/Symbol:** `scripts/update-models.js:325-381` (`DEPRECATED_MODEL_TTL_MS` :325, `updateDeprecatedModels` :335-381), call site `scripts/update-models.js:458` (BEFORE models.json overwrite); README grace replay `withDeprecatedForReadme` `:387-405`; runtime side `index.ts:371-392` (`activeDeprecatedModels`/`withDeprecated`).
**Signature:** `updateDeprecatedModels(modelsJsonPath: string, newModels: {id:string}[]): void`; TTL constant `14 * 24 * 60 * 60 * 1000`.
**Data Shape:** `deprecated-models.json` = `Record<modelId, JsonModel & { deprecatedAt?: ISO-string }>`. Runtime reads it as an embedded import; script reads/writes the file on disk.

### Decisive source
```js
for (const old of oldModels) {
    if (old && old.id && !currentIds.has(old.id) && !deprecated[old.id]) {
      deprecated[old.id] = { ...old, deprecatedAt: now };   // preserved on repeat runs
      added.push(old.id);
    }
}
for (const [id, entry] of Object.entries(deprecated)) {
    if (currentIds.has(id)) { delete deprecated[id]; resurrected.push(id); continue; }
    const removedAt = Date.parse(entry && entry.deprecatedAt ? entry.deprecatedAt : '');
    if (Number.isNaN(removedAt) || Date.now() - removedAt > DEPRECATED_MODEL_TTL_MS) {
      delete deprecated[id];
      evicted.push(id);
    }
}
```
Call-site comment (`:458` call, comment `:455-457`): "Move delisted models to deprecated-models.json **BEFORE** models.json is overwritten" — the function re-reads the OLD models.json itself.

**Flow:** sync run fetches fresh list → reconcile graveyard against it (delisted ⇒ tombstone with `deprecatedAt=now`; returned ⇒ resurrect/delete from graveyard; expired ⇒ evict permanently) → only then overwrite models.json → runtime at import time filters graveyard entries by TTL, strips the `deprecatedAt` metadata key, and `withDeprecated` appends survivors that are not already present. Pass-3 addition: the README generator replays the same grace window (`withDeprecatedForReadme` :387-405 — graveyard entries within TTL, minus `deprecatedAt`, appended after live models) so docs keep serving delisted-but-grace models; README cost cells switched to em-dash for free/missing instead of "Free"/"-".
**Invariant:** the grace clock NEVER resets on repeat syncs (existing entries keep their original stamp — only absent ids get `now`). Live data always wins on id conflict (`withDeprecated` seeds via a `seen` set of live ids first; the README replay seeds identically). An unparseable/missing `deprecatedAt` is treated as EXPIRED, not immortal. The runtime never mutates the graveyard file; it is a read-only consumer of the script's output. The README replay is a THIRD consumer of the same tombstone file (runtime import + script reconcile + docs render) — all three must share the one TTL constant or docs and runtime disagree about what is still in grace.
**Probe:** no dedicated unit test upstream — deterministic probe: run `updateDeprecatedModels` logic mentally against the three-way state machine (add/resurrect/evict) recorded above; the shipped repo state shows `deprecated-models.json` currently a single line (`{}`-style, 1 line at HEAD 4520704) with historical entries in git history. Coverage caveat: untested upstream.
**Coverage caveat:** scripts/update-models.js verified `no_recorded_issue` by check_index_coverage.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "updateDeprecatedModels", limit: 5 });
// → pi-hypercharm-provider.scripts.update-models.updateDeprecatedModels Function scripts/update-models.js 336-381
```

## Verdict
Adopt the tombstone-with-timestamp graveyard pattern for any curated-list-vs-live-API reconciliation. Adapt TTL to your product's session-length reality. Omit the specific file names.
