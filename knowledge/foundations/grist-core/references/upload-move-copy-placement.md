<!-- capsule-v2 -->
# Upload move-vs-copy placement — how do you relocate a registered upload into sandbox-visible storage without duplicating disk usage or orphaning cleanup?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** When an upload must become readable by sandboxed import code, when is it MOVED vs COPIED, and what happens to the old directory and the cleanup callback?

## tmpDir uploads move (old dir dies); foreign uploads copy (original untouched); idempotent if already inside
**Path/Symbol:** `app/server/lib/uploads.ts` — `moveUpload(uploadInfo, newDir)` (:379–400).
**Signature:** `moveUpload(uploadInfo: UploadInfo, newDir: string): Promise<void>`.
**Data Shape:** mutates `uploadInfo` IN PLACE via `Object.assign` — `{files, tmpDir, cleanupCallback}` are replaced; file basenames preserved; new location = fresh `grist-upload-*` subdir INSIDE `newDir`.

### Decisive source
```ts
export async function moveUpload(uploadInfo: UploadInfo, newDir: string): Promise<void> {
  if (uploadInfo.tmpDir && isPathWithin(newDir, uploadInfo.tmpDir)) {
    return;                                    // already within newDir — no-op
  }
  const { tmpDir, cleanupCallback } = await createTmpDir({ dir: newDir });
  const move: boolean = Boolean(uploadInfo.tmpDir);
  for (const f of uploadInfo.files) {
    const absPath = path.join(tmpDir, path.basename(f.absPath));
    await (move ? fse.move(f.absPath, absPath) : fse.copy(f.absPath, absPath));
    files.push({ ...f, absPath });
  }
  try { await uploadInfo.cleanupCallback(); }
  catch (err) {
    // This is unexpected, but if the move succeeded, let's warn but not fail on cleanup error.
    log.warn(`Error cleaning upload ${uploadInfo.uploadId} after move: ${err}`);
  }
  Object.assign(uploadInfo, { files, tmpDir, cleanupCallback });
}
```

**Flow:** caller asks to place upload under the sandbox userfiles dir → if it already lives inside that dir, return unchanged → else create a fresh tmp subdir under the target → temp-born files are MOVED (source dir then removed by running the OLD cleanup callback), foreign/non-temporary files are COPIED and the old callback still runs but must be a no-op for non-tmp sources → registry row mutated in place so existing `uploadId`s stay valid.
**Invariant:** mode bit = "was this upload temp-dir born?" (`Boolean(tmpDir)`) — NOT the caller's intent; old-cleanup failure after a successful move is a WARN not an error (the data is already safe at the destination; failing would double-delete or strand the new copy); `isPathWithin` guard makes repeated placement calls idempotent; basename flattening means subdirectory structure is never preserved — all files must be direct children (the `UploadInfo.tmpDir` doc comment states this requirement).
**Probe:** `test/server/lib/uploads.ts` (:93–146 moves a tmp-born upload — old dir gone, new dir nested exactly one level under target with same members — then moves a non-temp registration: source survives AND its fake cleanup spy is called once; final `cleanupAll` removes only registry-owned dirs).
**Caveat:** runner-blocked here; probe recorded as pinned assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "moveUpload isPathWithin fse.move fse.copy upload", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: in-place row mutation keyed by original birth medium, idempotence guard via path-containment check, warn-don't-fail post-move cleanup. Adapt the destination convention (grist targets the sandbox userfiles root). Omit any variant that deletes the source BEFORE the new copy is fully written — the move/copy ladder here is crash-safe precisely because cleanup of the old location happens last.
