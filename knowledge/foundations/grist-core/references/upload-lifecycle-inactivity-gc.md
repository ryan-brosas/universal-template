<!-- capsule-v2 -->
# UploadSet lifecycle & inactivity GC — how do server-side uploads expire without leaking disk space while staying alive during active use?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What owns a registered upload between HTTP admission and consumption, and what exact rules govern its expiry, identity reuse, and process-exit cleanup?

## In-memory registry + InactivityTimer per upload, ping-on-every-read
**Path/Symbol:** `app/server/lib/uploads.ts` — class `UploadSet` (:282–361): `registerUpload` (:289–296), `getUploadInfo` (:301–307), `cleanup` (:312–318), `cleanupAll` (:324–337), `_getUploadInfoWithoutAuthorization` (:354–360); singleton `globalUploadSet` (:364); module-load shutdown hook (:368); `INACTIVITY_CLEANUP_MS = 60*60*1000` (:36).
**Signature:** `registerUpload(files: FileUploadInfo[], tmpDir: string | null, cleanupCallback: CleanupCB, accessId: string | null): number`; `cleanup(uploadId): Promise<void>`.
**Data Shape:** `_uploads: Map<number, UploadInfo>` where `UploadInfo = {uploadId, files, tmpDir: string|null, cleanupCallback, cleanupTimer: InactivityTimer, accessId: string|null}`; `_nextId` monotonic counter.

### Decisive source
```ts
public registerUpload(files, tmpDir, cleanupCallback, accessId): number {
  const uploadId = this._nextId++;
  const cleanupTimer = new InactivityTimer(() => this.cleanup(uploadId), Deps.INACTIVITY_CLEANUP_MS);
  this._uploads.set(uploadId, { uploadId, files, tmpDir, cleanupCallback, cleanupTimer, accessId });
  cleanupTimer.ping();                    // clock starts AT REGISTRATION, not first use
  return uploadId;
}
private _getUploadInfoWithoutAuthorization(uploadId): UploadInfo {
  const info = this._uploads.get(uploadId);
  if (!info) { throw new ApiError(`Unknown upload ${uploadId}`, 404); }
  info.cleanupTimer.ping();               // EVERY read resets the GC clock
  return info;
}
public async cleanup(uploadId) {
  const info = this._getUploadInfoWithoutAuthorization(uploadId);
  info.cleanupTimer.disable();            // order: disable → delete → run callback
  this._uploads.delete(uploadId);
  await info.cleanupCallback();
}
shutdown.addCleanupHandler(null, () => globalUploadSet.cleanupAll()); // module load!
```

**Flow:** POST /upload parses multipart into a fresh tmp dir → `registerUpload` assigns monotonic id and arms a 1h inactivity timer that starts ticking immediately → any consumer resolving the id via `getUploadInfo` pings the timer, pushing expiry out another hour → idle timeout fires `cleanup`: timer disabled, map entry deleted, tmp dir removed → process exit (including signal kill) triggers `cleanupAll` via the module-load shutdown handler.
**Invariant:** upload ids are NEVER reused within a set lifetime (`_nextId` only resets in `cleanupAll`, which exists for tests); cleanup ordering must be disable-before-delete-before-callback so a concurrent ping cannot resurrect a dying upload; `cleanupAll` snapshots values, clears the map, and wraps each callback in try/catch so one poisoned cleanup cannot block the rest; the shutdown hook must be registered at module load because the `tmp` library's own atexit does not run on signal kill.
**Probe:** `test/server/lib/uploads.ts` (:148–195 stubs `Deps.INACTIVITY_CLEANUP_MS` to 400 ms — untouched upload dies while a `getUploadInfo`-touched sibling survives, then dies later; :68–73 pins id 2 issued after id 0 was cleaned up, i.e. no reuse; :79–81 pins `cleanupAll` invoking a no-dir fake callback).
**Caveat:** runner-blocked here (mocha suite needs repo toolchain); probes recorded as source-pinned assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "UploadSet registerUpload cleanup cleanupAll", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the registry shape: monotonic ids, per-entry inactivity timer armed at registration, ping-on-read, disable→delete→callback teardown order, module-load exit hook. Adapt the 1 h TTL and the `InactivityTimer` implementation (see `inactivity-timer.md` capsule for the counter-gated primitive). Omit the grist-specific `UploadInfo` fields you don't need — but keep `accessId` binding (see `upload-access-id-binding.md`); dropping it makes uploads readable cross-user.
