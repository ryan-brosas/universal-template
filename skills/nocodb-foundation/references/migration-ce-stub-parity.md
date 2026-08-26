<!-- capsule-v2 -->
|# Credit-plan CE stub — edition-paired no-op migrations keep version slots aligned

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** What does an EE-only migration look like on the CE side — and why ship a file whose job returns true?

## Path/Symbol
`packages/nocodb/src/modules/jobs/migration-jobs/nc_job_016_credit_plan_backfill.ts:CreditPlanBackfillMigration` (7–11, whole file).

**Signature:** `async job(): Promise<boolean>` — unconditional `return true` (= complete).

**Data Shape:** none. The 11-line file: imports, comment ("CE no-op — credits are EE-only. The EE override does the real backfill."), @Injectable class, constant-true job.

### Decisive source
```ts
/**
 * CE no-op — credits are EE-only. The EE override does the real backfill.
 */
@Injectable()
export class CreditPlanBackfillMigration {
  async job(): Promise<boolean> {
    return true;
  }
}
```

**Flow:** init-migration-jobs registers it in a version slot (DI-time isEE selects CE class vs EE implementation — migration-ee-ce-skew.md) → runner invokes job() → true marks the slot consumed → never runs again.

**Invariant:** (1) The stub must EXIST in CE so both editions consume identical version-slot numbering; omitting it desynchronizes every later migration's slot index (the exact failure mode migration-ee-ce-skew documents). (2) `return true` means "slot complete", not "nothing to do forever". (3) Confirms pass-4's note: nc_job_016 is NOT a second resume-ledger instance — the EE body lives outside this tree; the ledger pattern remains unique to nc_job_012.

**Probe:** no unit test upstream. Source-grounded probe: whole file cited above; pairing capsule migration-ee-ce-skew.md (v5/v6/v7 same-slot different-service selection).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "CreditPlanBackfillMigration", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt edition-paired stub migrations for version-slot parity when porting versioned runners across forks; adapt nothing else. Coverage caveat: no in-repo unit tests; source-grounded.
