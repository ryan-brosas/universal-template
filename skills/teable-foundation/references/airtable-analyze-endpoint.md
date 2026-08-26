<!-- capsule-v2 -->
# Airtable import analyze endpoint — how does one route serve base discovery AND dry-run planning?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the analyze route branch on `airtableBaseId` presence, and what does each mode return for the client's wizard?

## analyze dual mode
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts`:`analyze` (:181–206) with controller wrapper (:72–86).
**Signature:** `async analyze(ro: IImportAirtableAnalyzeRo): Promise<IImportAirtableAnalyzeVo>`.
**Data Shape:** no `airtableBaseId` ⇒ `{bases: [{id,name,permissionLevel}]}` (bases with `permissionLevel !== 'none'` only); with id ⇒ `{base: {id, tables:[{id,name,fieldCount,viewCount}], issues}}` where issues come from a full plan build (the dry run).

### Decisive source
```ts
if (!ro.airtableBaseId) {
  const bases = await client.listBases();
  return {
    bases: bases
      .filter((base) => base.permissionLevel !== 'none')
      .map(({ id, name, permissionLevel }) => ({ id, name, permissionLevel })),
  };
}
const tables = await client.getBaseSchema(ro.airtableBaseId);
const plan = buildAirtableImportPlan(tables);
return { base: { ..., issues: plan.issues } };
```

**Flow:** createClient enforces credential presence (`Either integrationId or accessToken is required`) → discovery mode lists bases and hides permissionless ones → planning mode builds the FULL import plan purely in memory (no side effects) so the client can preview table/field counts and degradation issues BEFORE committing to a stream.
**Invariant:** Analyze never mutates anything — the same pure planner (`buildAirtableImportPlan`) powers both the preview and the real import, so predicted issues match executed issues by construction. Provider failures surface as BadRequestException with human guidance via `formatAirtableImportError` (401 token hint; 403/404 scope hint).
**Probe:** Direct test: `airtable-formula-translator.spec.ts` pins translator refusals that feed these issues; schema-level issue shapes pinned by `airtable-schema-mapper.spec.ts` it('degrades unsupported types and reports issues') :338. Source anchor: `grep -cF "buildAirtableImportPlan" apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` returns 3 (import + two call sites).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"analyze listBases getBaseSchema IImportAirtableAnalyzeVo","limit":5,"detail":"ids"}'
```

## Verdict
Adopt pure-planner dual-mode analysis (discover + dry-run) before any long import; adapt VO shapes; omit Airtable permissionLevel vocabulary if targeting another provider. Coverage caveat: none.
