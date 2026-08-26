<!-- capsule-v2 -->
# EE/CE versioned-migration skew — the same version number runs DIFFERENT services per edition, converging on one state

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** When Enterprise and Community editions ship different data migrations for the same schema change, how does the version ladder keep both editions correct without double-applying?

## Path/Symbol
`packages/nocodb/src/modules/jobs/migration-jobs/init-migration-jobs.ts:InitMigrationJobs.migrationJobsList` (32–113) — entries `{version, job: MigrationJobTypes.X, service}`; runner `job()` at 142–242 (mechanics already covered by the `migration-jobs` capsule).

**Signature:** static list; service selection happens at CONSTRUCTION via DI (`isEE ? this.orderColumnMigration : this.noOpMigration`) — not at run time.

**Data Shape:** versions are strings compared with `+m.version > +migrationJobsState.version`. The skew trio:
- v5 `NoOpMigration`: EE runs OrderColumnMigration; CE runs no-op.
- v6 `OrderColumnCreation`: CE runs OrderColumnMigration; **EE runs no-op** (EE's v5 already did it).
- v7 `RecoverOrderColumnMigration`: CE runs recover; **EE runs no-op**.

### Decisive source
```ts
{ version: '5',  job: MigrationJobTypes.NoOpMigration,
  service: isEE ? this.orderColumnMigration : this.noOpMigration },
{ version: '6',  job: MigrationJobTypes.OrderColumnCreation,
  service: isEE ? this.noOpMigration : this.orderColumnMigration },   // EE already migrated in v5
{ version: '7',  job: MigrationJobTypes.RecoverOrderColumnMigration,
  service: isEE ? this.noOpMigration : this.recoverOrderColumnMigration },
```

**Flow:** each instance builds its list once with its own edition's services. The shared `nc_*` jobs-state store records only the highest COMPLETED version — it never knows which concrete service ran. An instance upgrading CE→EE (or vice versa) finds its stored version ≥ the skipped numbers and never replays them, so exactly one body ever executes per version per deployment.

**Invariant:** a version slot is an EDITION-SCOPED promise — "by v6 the order-column work is done" — not a specific function name. The no-op service is the mechanism that keeps the ladder dense and monotonic across editions; porters who instead REMOVE the EE entry renumber versions and break mixed-fleet state stores. The runner advances the version only when the service returns true (see `migration-jobs` capsule), so a real migration failing leaves the slot to retry while a no-op trivially succeeds.

**Probe:** no unit test upstream. Source-grounded probe: `init-migration-jobs.ts:53-67` (the three skewed slots verbatim) vs `:32-52, 68-113` (all other slots use the same service for both editions); runner interplay at `:178-234` (`+version` compare + advance-on-true).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "InitMigrationJobs migrationJobsList NoOpMigration isEE", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt edition-skewed version slots filled with explicit no-ops over renumbering; adapt to any multi-edition/multi-tenant fork of one migration ladder; omit the concrete order-column migrations unless porting that feature. Coverage caveat: no in-repo unit tests; source-grounded.
