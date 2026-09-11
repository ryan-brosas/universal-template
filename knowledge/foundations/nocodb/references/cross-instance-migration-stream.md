<!-- capsule-v2 -->
# Cross-instance base migration — how do you stream an entire base through one HTTP POST to another NocoDB install?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What frame order and error contract let the receiver import while the sender is still exporting?

## JSON-frame stream over octet-stream axios POST
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/export-import/migrate.service.ts:migrateBase` (:36-302) — terminator-safety comment (:108-115), pushStream null-terminator helper (:121-127), axios catch pushes null (:131-146), frame order (:148-217), per-model data/link pump (:222-295), shared handledMmList (:220); URL/secret validation in `migrate.controller.ts` (:44-70); sandbox guard :51-54.
**Signature:** target = `POST {instanceUrl}/api/v2/meta/duplicate/remote/{secret}` with `Content-Type: application/octet-stream`, `data: stream`, `maxBodyLength: Infinity`, SSRF-filtered agents via `getFilteredAgents({url, source: OperationSource.MIGRATION})`.
**Data Shape:** newline-free JSON frames `{type, data}` with types `base|users|schema|warnings|scripts|documents|dashboards|workflows|interfaces|data|link`; data/link frames add `modelId` and terminate their model's section with `data: null`.

### Decisive source
```ts
// everything below this line is live, and `migrateBase` has no try/catch,
// so a rejection past this point would skip the `pushStream(null)`
// terminator and leave the receiver holding an open request.
const extras = await this.collectMigrationExtras(context, { models, idMap });
…
const axiosPromise = axios({ method: 'post', url: targetUrl, headers: {
  'Content-Type': 'application/octet-stream' },
  ...getFilteredAgents({ url: targetUrl, source: OperationSource.MIGRATION }),
  data: stream, maxBodyLength: Infinity,
}).catch((e) => { pushStream(null); return e; });   // error ⇒ close the stream
pushStream({ type: 'base', … });                    // then base → users → schema →
…                                                   // warnings → extras msgs →
for (const sourceModel of models) {                 // scripts→docs→dashboards→workflows→interfaces (duplicate.processor order)
  // two Readables per model; producer errors push(null) BOTH streams and set a
  // SHARED error var checked at the top of every later iteration
  await Promise.all([dataStreamPromise, linkStreamPromise]);
}
pushStream(null);                                   // single true terminator
```

**Flow:** validate migration URL client-side (protocol allowlist http/https, origin + `secret` query param required), refuse sandbox contexts → serialize users/schema/scripts/workflows/dashboards/interfaces with `includeSubjectEmails: true` (target resolves users by EMAIL — ids are meaningless cross-instance) and `compatibilityMode: source.type !== 'pg'` → start the axios request BEFORE pushing frames (consumer-first, same as export-stream-upload) → emit frames in duplicate.processor's phase order so ids resolve against already-imported phases → stream each model as paired CSV data+link streams reusing export primitives (`streamModelDataAsCsv`) with ONE shared handledMmList deduping mm links across models → null-terminate.
**Invariant:** the terminator discipline is the whole protocol — any throw after streaming starts must still reach a `pushStream(null)` or the receiver hangs on an open request forever; that is why extras collection happens before the stream opens and why the axios catch itself closes the stream. Frame ORDER mirrors duplicate.processor because the receiving importer resolves aliases against earlier phases. Per-model sections end with explicit `data:null` sentinels so partial failures stay parseable.
**Probe:** no unit test upstream. Source-grounded probe: no-try/catch comment :108-111; catch-pushes-null :143-146; "Ordering below mirrors duplicate.processor" comment :180-183; shared handledLinks declared once above the loop :219-220.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "MigrateService migrateBase pushStream collectMigrationExtras getFilteredAgents", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the consumer-first + guaranteed-terminator streaming shape for any large cross-service transfer; adapt the frame vocabulary to your importer; omit the sandbox guard if you have no sandbox tier.
