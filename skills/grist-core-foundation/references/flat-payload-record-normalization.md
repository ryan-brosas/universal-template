<!-- capsule-v2 -->
# Flat-payload record normalization — how does POST /records accept three payload shapes while keeping one strict validator?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you support a loose "flat" convenience format without weakening the canonical RecordsPost contract?

## ?flat=1 wraps bare arrays into {records:[…]} IN PLACE, dropping unusable ids from loosely-shaped entries; validation runs after normalization
**Path/Symbol:** `app/server/lib/DocApi.ts:POST /tables/:tableId/records` (:566–593); validator `validateCore(RecordsPost, req, body)` (:585) → `app/server/lib/DocApiUtils.ts:validateCore` (:30–38).
**Signature:** route handler with `isAffirmative(req.query.flat)` branch; `ops.create(body.records)` via TableOperationsImpl.
**Data Shape:** canonical `{records: [{id?, fields}]}`; flat mode accepts a BARE array — each entry either already `{fields}` or a fields-object directly (`{col: val,…}`). Column-format twin lives at POST `/data` (BulkColValues, count derived from first column's length).

### Decisive source
```ts
// WARNING: The `req.body` object is modified in place.
let body = req.body;
if (isAffirmative(req.query.flat)) {
    if (!body.records && Array.isArray(body)) {
      for (const [i, rec] of body.entries()) {
        if (!rec.fields) {
          // If ids arrive in a loosely formatted flat payload,
          // remove them since we cannot honor them. If not loosely
          // formatted, throw an error later.
          if (rec.id) { delete rec.id; }
          body[i] = { fields: rec };
        }
      }
      body = { records: body };
    }
}
validateCore(RecordsPost, req, body);
```
**Flow:** opt-in via `?flat=1` → only when body lacks `.records` AND is an array → per-entry: entries WITH `.fields` pass through untouched (their ids survive → validated later, duplicate/explicit ids may throw); bare field-objects get wrapped as `{fields: rec}` and any `id` present on the loose object is DELETED because id+fields together would be ambiguous/honored inconsistently → reassemble `{records}` → strict checker runs on the normalized shape → create. Telemetry side-channel: `?utm_source=grist-forms` logs "submittedForm".
**Invariant:** normalization mutates req.body in place (documented WARNING — anything reading req.body later sees post-normalization data). The strict checker NEVER sees raw flat payloads; loosness is confined to the explicit opt-in flag. Id-dropping is deliberate and asymmetric: canonical-shape ids are honored (create validates them), flat-shape ids are discarded with a comment pointing at future query-param support.
**Probe:** `test/server/lib/docapi/DocApiRecords.ts` (records CRUD suite incl. create paths; coverage caveat: no dedicated flat-mode case found upstream — normalization ladder is source-pinned).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "flat records normalize validateCore RecordsPost TableOperationsImpl create", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt normalize-then-validate whenever adding a convenience format over a strict API. Adapt the flag name/wrapping shape freely; keep mutation-localized-and-documented or switch to cloning. Omit the id-dropping nuance only if your flat format never carries ids.
