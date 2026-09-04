<!-- capsule-v2 -->
# Upload access-id binding — how do you stop user B from reading (or deleting) user A's in-flight upload by guessing sequential ids?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the exact ownership token bound at registration, when may it legitimately be `null`, and what does an unauthorized read throw?

## accessId = userId:host stamped at register, enforced on EVERY resolve
**Path/Symbol:** `app/server/lib/uploads.ts` — `makeAccessId` (:569–583), `UploadSet.getUploadInfo` (:301–307); producers `handleOptionalUpload` (:240), `/copy` route (:90); consumers `DocManager.makeAccessId` (`app/server/lib/DocManager.ts`:597–599) and `ActiveDoc.makeAccessId` (`app/server/lib/ActiveDoc.ts`:2247–2249) which thread `gristServer` in as the host source.
**Signature:** `makeAccessId(worker: string | Request | GristServer, userId: number | null): string | null`; `getUploadInfo(uploadId: number, accessId: string | null): UploadInfo`.
**Data Shape:** access token = `` `${userId}:${host}` `` string or `null`; stored verbatim on the `UploadInfo` row.

### Decisive source
```ts
export function makeAccessId(worker: string | Request | GristServer, userId: number | null): string | null {
  if (isSingleUserMode()) { return null; }        // standalone: no auth model at all
  if (userId === null) { return null; }           // anonymous uploads are world-readable-by-design
  let host: string;
  if (typeof worker === "string") { host = worker; }
  else if ("getHost" in worker) { host = worker.getHost(); }
  else {
    const gristServer = (worker as RequestWithGrist).gristServer;
    if (!gristServer) { throw new Error("Problem accessing server with upload"); }
    host = gristServer.getHost();
  }
  return `${userId}:${host}`;
}
// enforcement:
public getUploadInfo(uploadId, accessId): UploadInfo {
  const info = this._getUploadInfoWithoutAuthorization(uploadId);
  if (info.accessId !== accessId) { throw new ApiError("access denied", 403); }
  return info;
}
```

**Flow:** upload lands → server stamps `makeAccessId(req, getUserId(req))` into the registry row → any later resolution must present the byte-identical `userId:host` pair → mismatch throws ApiError 403 BEFORE the timer-ping side effect matters to the caller; unknown id throws 404 regardless of accessId.
**Invariant:** strict-equality comparison — there is NO prefix/host-relaxed matching, so a worker behind a different host header cannot read another worker's upload even for the same user id; `null` accessId matches ONLY `null`-registered uploads (single-user mode or anonymous), so enabling multi-user mode silently orphans previously-null rows — a porter must decide that migration explicitly; the same token doubles as the mutation authority (`changeUploadName` routes through the authorized getter).
**Probe:** `test/server/lib/uploads.ts` (:301–330 registers under `"x42"`/`"x43"` — cross-access and null-access throw `/access denied/i`, unknown id throws `/unknown upload/i` for every accessId).
**Caveat:** runner-blocked here; probe recorded as pinned assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "makeAccessId getUploadInfo access denied", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt `userId:host` composite binding with strict equality and 403-on-mismatch. Adapt the host source (grist derives it from `GristServer.getHost()` / doc-worker tag); in a single-node service a constant host degenerates safely to plain userId. Omit per-request re-derivation tricks — the token is computed once at registration AND once at each consumption from the CURRENT request context; never persist or log it.
