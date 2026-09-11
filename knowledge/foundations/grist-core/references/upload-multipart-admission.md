<!-- capsule-v2 -->
# Multipart admission funnel — what does the /upload endpoint actually store, and why are size limits deliberately absent there?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Where should multipart bytes land, which field name carries files, how are extensions chosen, and where is the correct enforcement point for upload quotas?

## multiparty into per-request tmp dir; 'upload' field; guessExt; NO size limit at admission
**Path/Symbol:** `app/server/lib/uploads.ts` — `handleOptionalUpload` (:207–251), `handleUpload` (:123–127), `addUploadRoute` (:55–106) with OPTIONS pre-flight (:63–66) and abort-aware catch (:72–82); ext selection `guessExt` (`app/server/lib/guessExt.ts`:15–59); route mounting `FlexServer.ts`:2403 `addUploadRoute(this, this.app, this._docWorkerMap, trustOrigins, ...basicMiddleware)`.
**Signature:** `handleOptionalUpload(req: Request, res: Response): Promise<FormResult>` where `FormResult = {upload?: UploadResult, parameters?: {[key: string]: string}}`.
**Data Shape:** multiparty writes parts to `tmpDir` (prefix `grist-upload-`); each file becomes `FileUploadInfo {absPath, origName, size, ext}`; response exposes only `{origName, size, ext}` per file plus `uploadId` — `absPath` NEVER leaves the server.

### Decisive source
```ts
// Note that we don't limit upload sizes here, since this endpoint doesn't know what kind of
// upload it is, and some uploads are unlimited (e.g. uploading .grist files). Limits are
// checked in the client, and should be enforced on the server where an upload is processed.
const form = new multiparty.Form({ uploadDir: tmpDir });
const [formFields, formFiles] = await fromCallback((cb) => form.parse(req, cb), { multiArgs: true });
if (formFiles.upload) {
  for (const file of formFiles.upload) {
    uploadedFiles.push({
      absPath: file.path,
      origName: file.originalFilename,
      size: file.size,
      ext: await guessExt(file.path, file.originalFilename, mimeType),  // sniff, don't trust
    });
  }
  const accessId = makeAccessId(req, getUserId(req));
  const uploadId = globalUploadSet.registerUpload(uploadedFiles, tmpDir, cleanupCallback, accessId);
}
```
```ts
// addUploadRoute error path — resume the socket so the connection can be reused:
} catch (err) {
  req.resume();                                    // unblock abandoned body
  if (/Request aborted/.test(err.message)) { log.warn(...); } else { log.error(...); }
  res.status(err.status || 500).json({ error: err.message || "internal error" });
}
```

**Flow:** OPTIONS pre-answered 200 after origin middleware → POST streams parts straight to a fresh `grist-upload-*` dir → every file in form field **`upload`** is stat'd and extension-guessed → whole set registers as ONE upload under one accessId → handler returns `{uploadId, files:[{origName,size,ext}]}`; missing payload → ApiError("missing payload", 400).
**Invariant:** admission is storage-only — no quota, no type allowlist, no size cap HERE by design; enforcement belongs where the upload is *consumed* (import parsers, attachment caps), because the endpoint cannot know whether a `.grist` full-document upload or a bounded CSV import is arriving; the tmp dir + cleanupCallback pair must travel together INTO the registration so GC owns them from that instant; on failure the request stream must be resumed (`req.resume()`) or sockets leak.
**Probe:** `test/server/lib/uploads.ts` (:213–244 pins fetchURL naming/ext ladder via content-type vs URL extension; :327 DocApi `/api/docs/:docId/attachments` consumes `handleUpload(req,res)` then `activeDoc.addAttachments(uploadId)` in `app/server/lib/DocApi.ts`:325–330 — the consumption-side seam).
**Caveat:** runner-blocked here (route-level tests live in docapi suites needing full FlexServer); probes recorded as pinned assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "handleOptionalUpload handleUpload multiparty Form parse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: dedicated per-request tmp dir handed to the multipart parser, single reserved field name for files, extension sniffing over client-declared names, and quota enforcement at CONSUMPTION not admission. Adapt field name and ext policy to your product. Omit browser-side limit duplication as a security control — it's UX only here.
