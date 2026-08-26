<!-- capsule-v2 -->
# At-import failure policy — what survives when an Airtable import job dies halfway, and why can data errors "succeed"?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** Which artifacts of a failed at-import are rolled back, which are swallowed, and which state outlives the job?

## Two-tier failure policy: schema errors compensate, data errors swallow
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/at-import.processor.ts` — outer try/catch (:2579-2821), inner data-sync try/catch (:2691-2781), EE audit pair (:141-168 start, :2786-2801 error), rollback loop (:2803-2810), module-global name registry `namesRef`/`getUniqueNameGenerator` (:2827-2841), instance-wide `attachmentQueue` (:112).
**Signature:** `job(): Promise<void>` — throws only for schema-phase failures; data-phase failures never propagate.
**Data Shape:** rollback list = `ncSchema.tables` (only tables THIS run pushed via `updateNcTblSchema`); audit id = single `parentAuditId` nanoid reused by both audit records.

### Decisive source
```ts
// DATA PHASE — errors are logged and swallowed; the job still "succeeds":
} catch (error) {
  logBasic(`There was an error while migrating data! Please make sure your API key is correct.`);
  logBasic(`Data migration failed: ${error}`);
}   // ← no rethrow: execution continues to generateMigrationStats()

// OUTER CATCH — any schema-phase failure compensates before rethrowing:
} catch (e) {
  if (Noco.isEE()) {
    await Audit.insert(await generateAuditV1Payload<AirtableImportFailPayload>(
      AuditV1OperationTypes.AIRTABLE_IMPORT_ERROR,
      { context, details: { airtable_sync_id: syncDB.syncId, error: e?.message },
        req, id: parentAuditId }));                       // same id as start record
  }
  // delete tables that were created
  for (const table of ncSchema.tables) {
    await this.tablesService.tableDelete(context, { tableId: table.id,
      forceDeleteRelations: true, req });
  }
  ...
  throw e;
}
// module scope — OUTLIVES every job in the worker process:
const namesRef = {};
const getUniqueNameGenerator = (defaultName = 'name', context = 'default') => {
  const finalContext = `${context}_${defaultName}}`;
  if (!namesRef[finalContext]) namesRef[finalContext] = {};
  return (initName: string = defaultName): string => {
    let c = 0;
    while (name.toLowerCase() in namesRef[finalContext]) name = `${initName}_${++c}`;
    namesRef[finalContext][name.toLowerCase()] = true;
    return name;
  };
};
```

**Flow:** the job has exactly two failure tiers. Tier 1 — everything up to and including view configuration (schema fetch, base create/get, `nocoCreateBaseSchema`, LTAR, lookups, rollups, primary, views): any throw reaches the outer catch, which writes the EE error audit under the SAME `parentAuditId` minted at job start (:141), deletes every table this run created (pre-existing tables in sync-into-existing mode are untouched because only `updateNcTblSchema` pushes into `ncSchema.tables`), sends `a:airtable-import:error` telemetry, and rethrows so Bull marks the job FAILED. The BASE shell itself is never deleted — users see an empty/partial base, not a half-filled one. Tier 2 — the `syncData` loop wraps `importData` per-base in its own try/catch that logs and continues: a data-phase crash yields a SUCCESSFUL job with partial rows, then still emits the success summary and `a:airtable-import:success` telemetry. Porters who hoist the data call into the outer try invert this contract.
**Invariant:** (1) Compensation deletes TABLES, never the base — and only tables registered in `ncSchema.tables`. (2) The EE audit pair is keyed by one `parentAuditId`: start record and error record share it; CE inserts neither. (3) `namesRef` is MODULE-scoped and case-insensitively accumulates every generated `sheet_*` table_name / `column_*` name across ALL imports in the worker's lifetime — names of long-deleted tables stay reserved until restart, and two simultaneous imports in one process cannot collide (also cross-reserve). Its key template even carries a stray trailing `}` (`\`${context}_${defaultName}}\``) — harmless, but copy it or key collisions across generators occur. Seeding idiom: `uniqueTableNameGen(existingModel.table_name)` (:2629) calls the generator PURELY to register an existing name, discarding the return. (4) `attachmentQueue` (`PQueue concurrency 1`) is an INSTANCE field, not job-local: attachment URL downloads serialize across all concurrently running at-import jobs in the process — deliberate rate protection, surprising to porters who move it into `job()`.
**Probe:** no unit test upstream. Deterministic probes: `at-import.processor.ts:2775-2780` — inner catch has no `throw`; `:2804-2810` — rollback iterates `ncSchema.tables` only; `grep -n "namesRef" at-import.processor.ts` → declarations at module bottom (:2827-2841), outside the class; `:112` — `attachmentQueue` declared beside `debugLog`, not inside `job()`.
**Coverage caveat:** file indexed clean; claims from whole-file read at f7513664, not test-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "AtImportProcessor namesRef getUniqueNameGenerator attachmentQueue tableDelete forceDeleteRelations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier policy verbatim for any long-running importer: structural failures compensate (delete own creations, rethrow), data failures degrade gracefully (log, finish, report counts). Adapt the audit pairing to your observability stack — keep one correlation id for start+failure. OMIT the module-global name registry unless you need cross-job uniqueness; prefer explicit reserved-name sets passed per job. Keep heavy external fetches behind a process-shared concurrency-1 queue only if the upstream service is rate-limited per account, not per job.
