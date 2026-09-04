<!-- capsule-v2 -->
# BaseSyncTarget lazy wiring — how does a backend construct and memoize its FileApi/Synchronizer pair, and what happens when init races?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How should a sync-target base class lazily build shared services exactly once, and how must concurrent first callers behave?

## Lazy memoized accessors with a polling init-state machine
**Path/Symbol:** `packages/lib/BaseSyncTarget.ts:13-171` (`fileApi()` :126-130, `synchronizer()` :141-168, statics :20-63).
**Signature:** `async fileApi(): Promise<FileApi>; async synchronizer(): Promise<Synchronizer>; static id()/targetName()/label(); static unsupportedPlatforms(): string[]; async isAuthenticated(): Promise<boolean>; public syncStarted(): Promise<boolean>`.
**Data Shape:** instance holds `synchronizer_`, `initState_: 'started'|'ready'|'error'|null`, memoized `fileApi_`, injected `options_`/`db_`/`logger_`; static `dispatch` action sink defaulted to a no-op.

### Decisive source
```ts
public async fileApi() {
    if (this.fileApi_) return this.fileApi_;
    this.fileApi_ = await this.initFileApi();
    return this.fileApi_;
}
public async synchronizer(): Promise<Synchronizer> {
    if (this.synchronizer_) return this.synchronizer_;
    if (this.initState_ === 'started') {
        // Synchronizer is already being initialized, so wait here till it's done.
        return new Promise((resolve, reject) => {
            const iid = shim.setInterval(() => {
                if (this.initState_ === 'ready') { shim.clearInterval(iid); resolve(this.synchronizer_); }
                if (this.initState_ === 'error') { shim.clearInterval(iid); reject(new Error('Could not initialise synchroniser')); }
            }, 1000);
        });
    } else {
        this.initState_ = 'started';
        try {
            this.synchronizer_ = await this.initSynchronizer();
            this.synchronizer_.setLogger(this.logger());
            this.synchronizer_.setEncryptionService(EncryptionService.instance());
            this.synchronizer_.setResourceService(ResourceService.instance());
            this.synchronizer_.setShareService(ShareService.instance());
            this.synchronizer_.dispatch = BaseSyncTarget.dispatch;
            this.initState_ = 'ready';
            ...
        } catch (error) { this.initState_ = 'error'; throw error; }
    }
}
public static id(): number { throw new Error('id() not implemented'); }
```

**Flow:** first `synchronizer()` caller flips `initState_` to 'started' and awaits the subclass `initSynchronizer()` (which builds FileApi + wires logger, encryption/resource/share services, dispatch); concurrent callers poll `initState_` every second until 'ready' resolves or 'error' rejects; `fileApi()` memoizes independently and honors `setFileApi(v)` so tests can force several clients onto ONE shared api ("multiple clients can share and sync to the same file api"); `syncStarted()` requires synchronizer present AND authenticated AND `state() !== 'idle'`.
**Invariants:** (1) services attach AFTER construction via singleton `.instance()` lookups — the base class never takes them as constructor args; (2) an init failure latches `initState_='error'` and every waiter rejects — a later call retries from scratch because the latch is only checked while 'started'; (3) abstract identity statics (`id/targetName/label`) throw 'not implemented' rather than returning junk defaults, unlike capability statics which have real defaults (supportsSelfHosted=true, others false, unsupportedPlatforms=[]); (4) `checkConfig` is deliberately untyped-per-subclass (`any`) because option shapes differ per backend.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/joplin && grep -cF "this.initState_ = '"'"'started'"'"';" packages/lib/BaseSyncTarget.ts && grep -cF "if (this.fileApi_) return this.fileApi_;" packages/lib/BaseSyncTarget.ts && grep -cF "throw new Error('"'"'id() not implemented'"'"');" packages/lib/BaseSyncTarget.ts'` (anchored at repo root; expects 1 / 1 / 1). Direct read: concrete factory chain in `packages/lib/SyncTargetJoplinServer.ts:20-43` — `newFileApi`: JoplinServerApi → FileApiDriverJoplinServer → `new FileApi('', driver)` → `setSyncTargetId(id)` → `await fileApi.initialize()`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "BaseSyncTarget initSynchronizer initFileApi initState synchronizer fileApi", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: lazy memoized accessor pair, explicit started/ready/error latch for racing callers, service injection post-construction, setFileApi test-sharing hook, throw-not-default identity statics. Adapt: replace the 1s interval poll with a shared init promise on platforms where you control both callers. Omit: joplin's concrete service singletons.
