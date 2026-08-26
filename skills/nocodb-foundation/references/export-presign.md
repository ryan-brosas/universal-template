<!-- capsule-v2 -->
# Export filename/presign — how does an export job name its artifact deterministically and hand back a time-limited download URL?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What are the naming, mimetype, and presigned-URL rules around the exported file?

## dated filename + 3h presign
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-export/data-export.processor.ts:job` naming block (60-81) and presign branches (216-246).
**Signature:** filename = `` `${base.title} - ${model.title} (${view.title}) ${YYYY-MM-DD_HH-mm}` `` in `options.filenameTimeZone || 'Etc/UTC'`; `PresignedUrl.getSignedUrl({pathOrUrl, filename, expireSeconds: 3*60*60, preview: false, mimetype, encoding?})`.
**Data Shape:** destPath `nc/uploads/data-export/<YYYY-MM-DD>/<HH>/<modelId>/...`; extension map json/csv/xlsx/ics; mimetypes `application/json | text/csv | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet | text/calendar`.

### Decisive source
```ts
const date = dayjs().tz(options?.filenameTimeZone || 'Etc/UTC').format('YYYY-MM-DD_HH-mm');
const filename = `${base.title} - ${model.title} (${getViewTitle(view)}) ${date}`;
...
// if url is not defined, it is local attachment
if (!url) {
  url = await PresignedUrl.getSignedUrl({
    pathOrUrl: path.join(destPath.replace('nc/uploads/', '')),
    ...
  });
} else {
  url = await PresignedUrl.getSignedUrl({ pathOrUrl: url, ... });   // remote object url
}
return { timestamp: new Date(), extension_id, type: exportAs, title: filename, url };
```

**Flow:** after the concurrent pump/upload (export-stream-upload capsule), the job signs either the LOCAL path (adapter returned nothing) or the REMOTE object URL, always 3-hour expiry, with encoding attached for text formats but omitted for binary xlsx. The job's return value becomes the job RESULT the client polls for.
**Invariant:** the timezone default must be UTC — client-supplied zones only affect the human-readable timestamp, never the folder partitioning (which stays server-local `dayjs()`). Excel must not carry an `encoding` field into presign or downloads may be transcoded wrongly. Result shape `{url, title, type}` is what jobs-polling clients consume.
**Probe:** no unit test upstream. Source-grounded probe: `data-export.processor.ts:226-235` vs `:236-245` — the two presign branches differing only in pathOrUrl source; `:90-93` — excel excluded from setEncoding.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getSignedUrl PresignedUrl destPath data-export", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt deterministic human-readable filenames with UTC-defaulted timestamps and uniform presign expiry; adapt path scheme/mimetype map to host; omit ICS view-visibility restriction (public-export concern). Coverage caveat: no in-repo tests; source-grounded.
