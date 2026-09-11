<!-- capsule-v2 -->
# Timestamped sync-info LWW merge — how do disconnected clients agree on E2EE state and app floors without a coordinator?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How is the shared `info.json` (version, e2ee, master keys, ppk, appMinVersion) merged when two clients changed different fields offline?

## SyncInfo merge kernel
**Path/Symbol:** `packages/lib/services/synchronizer/syncInfoUtils.ts` :263-302 (`mergeSyncInfos`), :236-260 (`mergeActiveMasterKeys`), :308-507 (`SyncInfo` class), :598-610 (`checkIfCanSync`).
**Signature:** `mergeSyncInfos(s1: SyncInfo /*local*/, s2: SyncInfo /*remote*/): SyncInfo`; every field stored as `{ value, updatedTime }`.
**Data Shape:** info.json on target + `syncInfoCache` Setting locally; per-field timestamps decide wins; master keys merged by id with `updated_time` newest-wins.

### Decisive source
```ts
output.setWithTimestamp(s1.keyTimestamp('e2ee') > s2.keyTimestamp('e2ee') ? s1 : s2, 'e2ee');
...
// We use >= so that the version from s1 (local) is preferred to the version in s2 (remote).
output.appMinVersion = compareVersions(s1.appMinVersion, s2.appMinVersion) >= 0 ? s1.appMinVersion : s2.appMinVersion;
```
Active-master-key override ladder (`mergeActiveMasterKeys`): if one key enabled & other not → pick the ENABLED one; else if one hasBeenUsed & other not → pick the USED one; else fall back to newer timestamp. Comment documents the exact mis-port this prevents: client 2 enabling E2EE later must not resurrect an unused duplicate key over client 1's already-used key.

**Flow:** start() fetches remote info.json → `syncInfoEquals` (fast-deep-equal on toObject) short-circuits identical states → else merge → upload newInfo under exclusive lock (dormant at pin) → save locally; e2ee flip side-effects run setupAndEnable/DisableEncryption; revisionService.* copied back into Settings ONLY when `keyTimestamp > 0` (0 = "never explicitly set" — prevents migration defaults stomping user customizations).
**Invariants:** (1) EVERY scalar decision is timestamp-LWW — never field-presence order; (2) bootstrap stamps `updatedTime: 0` for derived-from-settings fields so any explicit later change anywhere wins (comment :98-109); (3) local preferred on appMinVersion ties via >=; (4) `fixSyncInfo` clears activeMasterKeyId pointing at a missing key; loading migrates missing `hasBeenUsed` to TRUE (assume used — conservative); (5) forward-compat: `appMinVersion === '3.7.0' && noteLockKey !== null` fails checkIfCanSync — older clients must refuse locked-note targets instead of corrupting them.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/joplin && grep -cF "setWithTimestamp(s1.keyTimestamp('"'"'e2ee'"'"') > s2.keyTimestamp('"'"'e2ee'"'"')" packages/lib/services/synchronizer/syncInfoUtils.ts && grep -cF "always pick the enabled one regardless of usage" packages/lib/services/synchronizer/syncInfoUtils.ts && grep -cF "mk.hasBeenUsed = true;" packages/lib/services/synchronizer/syncInfoUtils.ts'` (anchored at repo root; expects 1 / 1 / 1). Direct tests: `packages/lib/services/synchronizer/syncInfoUtils.test.ts` — 'should merge sync target info, but should not make a disabled key the active one' (:192), 'should preserve a v3.7.0 version stored in the sync info cache' (:383), revision-timestamp merge tests (:477+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "mergeSyncInfos mergeActiveMasterKeys setWithTimestamp keyTimestamp appMinVersion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: {value, updatedTime} envelope + per-field LWW, enabled>used>timestamp key ladder, timestamp-0 bootstrap semantics, active-key dangling-clear, forward-compat floor refusal. Adapt: field set to your schema. Omit: ppk/noteLockKey specifics unless porting E2EE too.
