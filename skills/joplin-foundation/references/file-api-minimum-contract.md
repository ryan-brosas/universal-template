<!-- capsule-v2 -->
# FileApi adapter surface — what is the minimum operation set a new storage backend must implement, and which hooks are optional?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** Which FileApi operations does the synchronizer actually require from every driver, and how do optional capability hooks degrade?

## Six required ops + idempotent initialize + per-sync temp dir
**Path/Symbol:** `packages/lib/file-api.ts:180-190` (constructor + `initialize`), :298-301 (`tempDirName`), :401-409 (`put`); consumer `packages/lib/Synchronizer.ts:495-496`; conformance test `packages/lib/file-api-driver.test.ts:1-68`.
**Signature:** `new FileApi(baseDir: string | (()=> string), driver)`; `async initialize(); put(path, content, options?): Promise<>; get(path); stat(path): {path, updated_time, isDir?}; list(path): {items, hasMore, context}; mkdir(path); delete(path); clearRoot()`.
**Data Shape:** constructor injects a back-reference `this.driver_.fileApi_ = this` so drivers can reach FileApi helpers; `stat.updated_time` is the only stat field the sync kernel truly needs.

### Decisive source
```ts
public constructor(baseDir, driver) { this.baseDir_ = baseDir; this.driver_ = driver; this.driver_.fileApi_ = this; }
public async initialize() {
    if (this.initialized_) return;
    this.initialized_ = true;
    if (this.driver_.initialize) return this.driver_.initialize(this.fullPath(''));
}
// Synchronizer.ts, once per sync run, before fetchSyncInfo:
await this.api().initialize();
this.api().setTempDirName(Dirnames.Temp);
```
```ts
// file-api-driver.test.ts pins the minimum contract against ANY backend:
it('should create a file', ...put/get roundtrip...);
it('should get a file info', ...stat.path / !!stat.updated_time / stat.isDir false...);
it('should create a file in a subdirectory', ...mkdir + put...);
it('should list files', ...list(path).items paths...);
it('should delete a file', ...delete + list empty...);
// beforeEach: await fileApi().clearRoot();
// test comment: "Although the stat object includes an "isDir" property, this is
//                not actually used by the synchronizer so not required by any sync target."
```

**Flow:** each sync run calls `initialize()` (idempotent latch → optional driver hook for root setup) and then `setTempDirName(Dirnames.Temp)` — the temp dir name is per-run state because lock/temp traffic lives under well-known prefixes; every subsequent operation is `FileApi method → fullPath(path) → driver method`, with drivers able to call back via `fileApi_`. Capability predicates (`supportsLocks/supportsMultiPut/supportsMultiDelete/supportsAccurateTimestamp`) let drivers declare what they CAN do; everything undeclared degrades to the loop/fallback path at callers.
**Invariants:** (1) a new backend must satisfy only put/get/stat/mkdir/list/delete (+clearRoot for tests) — that six-op suite runs unchanged against memory/local/WebDAV drivers via the shared test env's `fileApi()`; (2) `isDir` on stats is optional (no consumer in the kernel); (3) `tempDirName()` throws 'Temp dir not set!' if used before the per-sync `setTempDirName` — code touching temp space (e.g. the clock probe) depends on that call having happened; (4) `initialize()` must stay re-entrant cheap: it latches BEFORE awaiting the driver hook.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/joplin && grep -cF "if (this.driver_.initialize) return this.driver_.initialize(this.fullPath('"'"''"'"'));" packages/lib/file-api.ts && grep -cF "await this.api().initialize();" packages/lib/Synchronizer.ts && grep -cF "this.api().setTempDirName(Dirnames.Temp);" packages/lib/Synchronizer.ts && grep -cF "await fileApi().clearRoot();" packages/lib/file-api-driver.test.ts'` (anchored at repo root; expects 1 / 1 / 1 / 1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "FileApi initialize tempDirName supportsMultiPut supportsAccurateTimestamp clearRoot", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: thin path-resolving wrapper over a driver, optional-hook initialization with an early latch, per-run temp-dir naming, capability predicate pattern instead of subclass hierarchies. Adapt: op set to your storage's semantics. Omit: joplin's lock operations on FileApi (owned by the lock capsules).
