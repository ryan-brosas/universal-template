<!-- capsule-v2 -->
# Insert restore-identity resolution — how are restored records' audit identities resolved without poisoning the write transaction?

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When inserting (or restoring) records, who authors `__created_by`/`__last_modified_by`, and why does the optional identity lookup run on a different connection?

## Restore-identity resolution ladder
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordRepository.ts:insert` (:1120–1147), `resolveRestoreActorIdentity` (:1095), `insertMany` (:1404–1486).
**Signature:** `resolveRestoreActorIdentity(actorLookupDb, userId?: string|null, fallback: ActorIdentity): Promise<ActorIdentity>`; used as `restoreValues?.createdBy === actorId ? actorIdentity : {}`.
**Data Shape:** `restoreRecordsById?: Map<recordId, {version?, createdTime?, createdBy?, lastModifiedTime?, lastModifiedBy?, autoNumber?, orders?, extraColumnValues?}>`; `ActorIdentity = {actorName?, actorEmail?}`; lookups hit `this.metaDb`, never the tx-scoped `db`.

### Decisive source
```ts
// Resolve actor identity outside transaction-scoped connection to avoid
// marking the current transaction as aborted when optional lookup fails.
const actorLookupDb = this.metaDb as unknown as Kysely<DynamicDB>;
const createdByIdentity = await this.resolveRestoreActorIdentity(
  actorLookupDb,
  restoreValues?.createdBy,
  restoreValues?.createdBy === actorId ? actorIdentity : {}
);
const lastModifiedByIdentity = await this.resolveRestoreActorIdentity(
  actorLookupDb,
  restoreValues?.lastModifiedBy ?? undefined,
  restoreValues?.lastModifiedBy === restoreValues?.createdBy
    ? createdByIdentity
    : restoreValues?.lastModifiedBy === actorId ? actorIdentity : {}
);
```

**Flow:** primary actor resolved first (context names win, else one `public.users` probe, failures degrade warn-only to `{}`); restore identities reuse the actor identity when IDs match instead of re-probing; `lastModifiedBy` falls back to the *createdBy* identity when equal. `insertMany` wraps the same ladder in a `restoreIdentityCache: Map<userId, ActorIdentity>` so N restorations cost ≤N probes total.
**Invariant:** optional identity lookups NEVER run on the transaction-scoped connection — a failed lookup there aborts every subsequent statement in the tx (`25P02`); degrade to `{}` names, never throw. Identity reuse is by ID equality, not by re-query.
**Probe:** `record/repository/PostgresTableRecordRepository.insert.pglite.spec.ts` (insert returns stored audit snapshots via mutation capture; restore paths exercise the identity fallbacks).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "resolveRestoreActorIdentity insert restore identity", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the separate-connection lookup rule and the ID-equality identity reuse ladder (porters routinely put the users probe inside the tx and lose the whole batch on a benign miss). Adapt the `ActorIdentity` shape to your auth model. Omit the concrete `public.users` schema.
