<!-- capsule-v2 -->
# URL fetch admission ladder — how do you turn an arbitrary user-supplied URL into a registered upload without trusting the network's story about what it fetched?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Which fetch agent handles which URL class, how is the filename derived when the URL is opaque, and which failures become which HTTP errors?

## untrusted-proxy vs internal fetch; Drive special-case; content-disposition naming; EPROTO→400 map
**Path/Symbol:** `app/server/lib/uploads.ts` — `fetchURL` (:438–440), `_fetchURL(url, accessId, options, isInternal?)` (:448–503), `_checkForError(response)` (:535–561); `Deps = {fetch: fetchUntrustedWithAgent, fetchInternal: fetch}` (:39–44); `fetchDoc` (:509–532) as the internal caller.
**Signature:** `fetchURL(url: string, accessId: string | null, options?: FetchUrlOptions): Promise<UploadResult>`; internal flag selects the agent.
**Data Shape:** success → single-file upload `{uploadId, files:[{origName,size,ext}]}` written to a fresh tmp dir as literal `upload-content`; failure → `ApiError(status)`.

### Decisive source
```ts
if (isDriveUrl(url)) {
  response = await downloadFromGDrive(url, code);
  fileName = "";                       // Read the file name from headers.
} else {
  const fetchFunc = isInternal ? Deps.fetchInternal : Deps.fetch;   // trusted vs proxy-agent split
  response = await fetchFunc(url, { redirect: "follow", follow: 10, headers });
}
await _checkForError(response);
if (fileName === "") {
  const disposition = response.headers.get("content-disposition") || "";
  fileName = contentDisposition.parse(disposition).parameters.filename || "document.grist";
}
const destPath = path.join(tmpDir, "upload-content");   // any name will do — fileName may be invalid
await new Promise((resolve, reject) => {                // stream to disk, never buffer whole body
  const dest = fse.createWriteStream(destPath, { autoClose: true });
  response.body.on("error", reject); dest.on("error", reject);
  dest.on("finish", resolve); response.body.pipe(dest);
});
// error translation:
if (err?.code === "EPROTO" || err?.code === "ECONNREFUSED" || err?.code === "ENOTFOUND") {
  throw new ApiError(`Can't connect to the server. The URL seems to be invalid. Error code ${err.code}`, 400);
}
```
```ts
// _checkForError: HTML-success sniffing (login-page detection):
if (response.ok) {
  if (contentType?.startsWith("text/html")) {
    if (response.url.startsWith("https://accounts.google.com")) {
      throw new ApiError("Importing directly from a Google Drive URL is not supported yet...", 403);
    }
    throw new ApiError("Could not import the requested file, check if you have all required permissions.", 403);
  }
  return;
}
```

**Flow:** public URL → `fetchUntrustedWithAgent` (proxy-agent wrapped, SSRF-hardened) OR internal doc-worker URL → `fetchInternal` plain node-fetch (see `fetchDoc`) → Drive URLs divert to the API downloader with header-derived filename → status/HTML checks run BEFORE any disk write → body pipes to `upload-content` in a fresh tmp dir → ext guessed from final fileName + content-type → registered under the CALLER-provided accessId.
**Invariant:** the two agents are NOT interchangeable — public/user URLs must traverse the untrusted proxy agent (egress control) while doc-worker URLs must BYPASS it (`GRIST_PROXY_FOR_UNTRUSTED_URLS` would break internal routing); a 200 with `text/html` body is an ERROR (auth redirect/login page), detected by content-type sniffing not status; filename precedence = explicit option > content-disposition > `"document.grist"` fallback, and the on-disk name is always fixed (`upload-content`) because remote names can contain path junk; network-layer codes (EPROTO/ECONNREFUSED/ENOTFOUND) map to 400 with the code embedded so clients see WHY the URL was bad.
**Probe:** `test/server/lib/uploads.ts` (:197–261 fetchURL block stubs `Deps.fetch` and pins: csv content-type names the file from URL basename with `.csv` ext (:213–220), text/plain shadowed by URL extension (:222–245), public path uses `Deps.fetch` and rejects if `fetchInternal` would fire (:247–260)); :263–298 fetchDoc block pins the inverse — internal worker URL uses `fetchInternal` only and hits `api/docs/<docId>/download`.
**Caveat:** runner-blocked here; probes recorded as pinned assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "_fetchURL fetchUntrustedWithAgent _checkForError content-disposition", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: dual-agent split keyed by URL trust class, HTML-as-error sniffing after 2xx, streamed-to-fixed-name disk write, coarse network-code→400 mapping. Adapt the Drive branch out if you have no Drive import (it degrades cleanly to the generic path). Omit trust in content-length or remote filenames entirely.
