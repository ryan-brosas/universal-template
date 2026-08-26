<!-- capsule-v2 -->
# Cross-worker doc copy — how does /copy turn a docId on ANOTHER doc worker into an upload on THIS one, and why does 403 get its own response shape?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the resolution chain from urlId to internal download URL, which credentials travel, and what does `template=1` change?

## transitive headers + raw docId lookup + worker-internal URL + isInternal bypass
**Path/Symbol:** `app/server/lib/uploads.ts` — `fetchDoc(server, docWorkerMap, urlId, req, accessId, template)` (:509–532); `/copy` route (:86–105); worker resolution `Deps.getDocWorkerInfoOrSelfPrefix` (:524).
**Signature:** `fetchDoc(server: GristServer, docWorkerMap: IDocWorkerMap, urlId: string, req: Request, accessId: string | null, template: boolean): Promise<UploadResult>`.
**Data Shape:** downloads via `GET {docWorkerInternalUrl}/api/docs/{docId}/download?template={0|1}` with the ORIGINAL request's transitive headers; result registers as a normal single-file upload.

### Decisive source
```ts
const headers = getTransitiveHeaders(req, { includeOrigin: false });  // forward user creds
// Resolve urlId to the full docId needed to find the right doc worker.
const docId = (await server.getHomeDBManager().getRawDocById(urlId)).id;
const { selfPrefix, docWorker } = await Deps.getDocWorkerInfoOrSelfPrefix(docId, docWorkerMap, server.getTag());
const docWorkerUrl = docWorker ? docWorker.internalUrl : getUrlFromPrefix(server.getHomeInternalUrl(), selfPrefix);
const apiBaseUrl = docWorkerUrl.replace(/\/*$/, "/");
const url = new URL(`api/docs/${docId}/download?template=${Number(template)}`, apiBaseUrl);
// The doc worker URL is trusted and internal. Bypass GRIST_PROXY_FOR_UNTRUSTED_URLS to prevent connection failures.
return _fetchURL(url.href, accessId, { headers }, /* isInternal */ true);
```
```ts
// /copy route error shape:
} catch (err) {
  if ((err as ApiError).status === 403) {
    res.status(403).json({ error: "Insufficient access to document to copy it entirely" });
    return;
  }
  throw err;
}
```

**Flow:** POST `/copy?doc=<urlId>[&name=][&template=1]` → urlId resolved to raw docId through the home DB (NOT string-parsed from the URL) → doc-worker map (or self-prefix fallback for single-process deployments) finds the owning worker's INTERNAL url → download streams through `_fetchURL(isInternal=true)` so the untrusted-proxy agent is bypassed → optional rename via `changeUploadName(uploadId, accessId, name)` → upload returned like any other.
**Invariant:** credentials ride the request's own transitive headers (Cookie etc.) — no service token minting; the internal/public URL choice matters (`internalUrl` for server-to-server) and trailing slashes are normalized before `new URL` joining; `template=1` asks the source worker for a structure-only export (no data rows); a 403 bubbling out of ANY layer must surface as the fixed "Insufficient access to document to copy it entirely" JSON rather than the generic handler — the client UI keys on this message.
**Probe:** `test/server/lib/uploads.ts` (:263–298 stubs homeDB `getRawDocById`, `getDocWorkerInfoOrSelfPrefix`, both fetch flavors — asserts ONLY `fetchInternal` fires and the called URL contains `api/docs/doc123/download`).
**Caveat:** runner-blocked here; probe recorded as pinned assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "fetchDoc getDocWorkerInfoOrSelfPrefix getTransitiveHeaders internalUrl download", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: id-resolution-before-routing, header-pass-through auth, internal-URL fetch with proxy bypass, fixed 403 message contract. Adapt worker discovery to your topology (grist's map-or-self-prefix fallback degrades to single-node cleanly). Omit public-URL round-tripping — copying through the load balancer would lose the trusted-agent guarantee.
