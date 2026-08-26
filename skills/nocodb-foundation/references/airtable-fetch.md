<!-- capsule-v2 -->
# Airtable fetch layer — how does the importer talk to Airtable's private web API without an API key, and what does it cache?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How do FetchAT.initialize/read/readView work over the shared-base protocol?

## shareId session + schema/view reads
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/helpers/fetchAT.ts:FetchAT` (whole, 250L).
**Signature:** `initialize(shareId, appId?): Promise<void>`; `read(): Promise<{baseId, schema}>`; `readView(viewId): Promise<{view}>`; `readTemplate(exploreId)` for `exp*` shares.
**Data Shape:** session params captured from the share endpoint (payload/appLoad first page); subsequent calls POST to airtable's internal endpoints with those cookies/params; response JSON carries `tableSchemas[].appTables{...}`.

### Decisive source
```ts
// job-side entry points into FetchAT (at-import.processor.ts:314-360):
if (!sDB.shareId) throw { message: 'Invalid Shared Base ID :: Ensure www.airtable.com/<SharedBaseID> is accessible. ...' };
if (sDB.shareId.startsWith('exp')) {
  const template = await FetchAT.readTemplate(sDB.shareId);
  await FetchAT.initialize(template.template.exploreApplication.shareId);
} else {
  await FetchAT.initialize(sDB.shareId, sDB.appId);
}
const ft = await FetchAT.read();          // whole-base schema in one call
const ftv = await FetchAT.readView(viewId); // per-view records for gallery/form data
```

**Flow:** initialize resolves the share link into a session; read() pulls the full base schema once (`rtc.fetchAt` stats time each call); readView() pages view-specific records that the schema doesn't include. The processor wraps every FetchAT call with counters feeding its perf log.
**Invariant:** one initialization per import — re-initializing mid-run invalidates captured session state. The `exp*` prefix path must resolve template→inner shareId BEFORE initialize. All errors surface as the user-facing "Invalid Shared Base ID" guidance since the common failure is a stale/private share link.
**Probe:** no unit test upstream. Source-grounded probe: `at-import.processor.ts:316-349` — branch + error message verbatim; `fetchAT.ts` — initialize/read/readView method trio over the shared endpoints.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "FetchAT initialize read readView shareId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the initialize-once/read-many session shape against any remote schema API; adapt to official APIs where possible (this targets a private protocol — highest adapt-cost capsule); omit readTemplate unless importing explore links. Coverage caveat: no in-repo tests; source-grounded.
