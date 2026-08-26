<!-- capsule-v2 -->
# SyncTargetRegistry platform composition — how do you expose pluggable sync backends whose availability differs per platform without forking ids?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** Where do backend classes get registered, why are numeric ids stable across platforms, and which metadata travels with a registration?

## Static id-keyed registry filled by per-platform composition roots
**Path/Symbol:** `packages/lib/SyncTargetRegistry.ts:15-110` (`class SyncTargetRegistry`); composition roots `packages/lib/BaseApplication.ts:763-772`, `packages/app-mobile/root.tsx:79-88`, `packages/app-mobile/utils/buildStartupTasks.ts:54-63`, `packages/lib/testing/test-utils.ts:127-137`.
**Signature:** `static addClass(t: typeof BaseSyncTarget); static classById(id): typeof BaseSyncTarget; static nameToId(name): number; static infoByName(name): SyncTargetInfo; static idAndLabelPlainObject(os, includeKeys?)`.
**Data Shape:** `reg_: Record<numericId, typeof BaseSyncTarget>`; `SyncTargetInfo { id, name, label, supportsSelfHosted, supportsConfigCheck, supportsRecursiveLinkedNotes, supportsShare, description, classRef }` — every field read off STATIC methods of the class.

### Decisive source
```ts
private static reg_: Record<string, typeof BaseSyncTarget> = {};
public static classById(syncTargetId: number) {
    const info = SyncTargetRegistry.reg[syncTargetId];
    if (!info) throw new Error(`Invalid id: ${syncTargetId}`);
    return info;
}
...
public static nameToId(name: string) { ... throw new Error(`Name not found: ${name}. Was the sync target registered?`); }
public static optionsOrder(): string[] { return ['0','10','7','3']; } // None, Joplin Cloud, Dropbox, OneDrive
// idAndLabelPlainObject: if (info.classRef.unsupportedPlatforms().indexOf(os) >= 0) continue;
```

**Flow:** app boots → ONE platform composition root calls `addClass` for its supported subset (tests additionally register `SyncTargetMemory`; mobile omits nothing the desktop list has except by platform filter) → settings/UI resolve user choice via `nameToId`/`classById`, both throwing loudly when a target was never registered → UI lists derive from `idAndLabelPlainObject(os)` which silently drops targets whose class declares `unsupportedPlatforms()` containing the current OS → display order comes from the pinned `optionsOrder()` array, not insertion order.
**Invariants:** (1) the registry starts EMPTY — membership is a per-platform capability declaration, so a missing `addClass` surfaces as "Was the sync target registered?" not a silent null; (2) ids are the durable cross-platform key (settings store `sync.target` as id) — never renumber, only extend; (3) capability metadata lives on static class methods so `infoByName` needs no instantiation; (4) `isJoplinServerOrCloud(id)` is the canonical membership triple used by when-clause state.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "public static optionsOrder()" packages/lib/SyncTargetRegistry.ts && grep -cF "SyncTargetRegistry.addClass(SyncTargetMemory);" packages/lib/testing/test-utils.ts && grep -cF "// Joplin Cloud" packages/lib/SyncTargetRegistry.ts'` (anchored at repo root; expects 1 / 1 / 1). Direct tests: `packages/lib/services/commands/stateToWhenClauseContext.test.ts:147-164` iterates ALL registered ids asserting `joplinServerConnected === isJoplinServerOrCloud(id)`; `packages/lib/models/settings/settingValidations.test.ts:18-25` resolves 'memory'/'dropbox' by name.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "SyncTargetRegistry classById nameToId addClass optionsOrder unsupportedPlatforms", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: empty-until-composed static registry keyed by stable numeric ids, loud throw-on-unregistered, static-method capability metadata, OS-based filtering, pinned display order. Adapt: the metadata fields to your product's flags. Omit: joplin's specific target set and UI label strings.
