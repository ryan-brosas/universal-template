<!-- capsule-v2 -->
# Restore identity choreography — how does restoring trashed records preserve ORIGINAL created-by/created-time while keeping lastModifiedBy resolution off the transaction?

**Source:** teable AGPL `develop@06a4461e`. **Question:** Restores must rewrite audit columns to historical actors — what is the exact fallback chain and why do actor lookups run outside the tx-scoped connection?

## snapshot values → cached per-user lookup → current actor; lookups on metaDb only
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `insert` restore plumbing (:1140–1156), `insertMany` cached resolver (:1406–1423), `resolveUpdateActorIdentity` (:1107–1118), `resolveActorIdentity` (:3362–3395, query `FROM public.users u WHERE u.id = ${actorId}::text LIMIT 1` :3372–3377), comment "Resolve actor identity outside transaction-scoped connection…" (:1138–1139). Tests: update.spec.ts 'uses resolved actor identity for lastModifiedBy snapshots on update' (:695); insert spec 'returns stored insert snapshots…' (:372).
**Signature:** `resolveActorIdentity(db, actorId, actorContext: {actorName?, actorEmail?}): Promise<ActorIdentity>`.

### Decisive source
```ts
// Resolve actor identity outside transaction-scoped connection to avoid
// marking the current transaction as aborted when optional lookup fails.
const actorLookupDb = this.metaDb;
const actorIdentity = await this.resolveActorIdentity(actorLookupDb, actorId, actorContext);
// per-record restore values win over looked-up identities:
...(restoreValues?.createdBy ? { createdBy: restoreValues.createdBy } : {}),
...(restoreValues?.lastModifiedBy === restoreValues?.createdBy ? createdByIdentity : ...)
```
```ts
try { /* users lookup */ } catch (error) {
  this.logger.warn('record:resolve_actor_identity_failed', {...});
  return { actorName: actorContext.actorName, actorEmail: actorContext.actorEmail };  // degrade, never throw
}
```

**Flow:** resolve the CURRENT actor's name/email once up front (context override → users-table lookup → warn-and-degrade) → per restored record, prefer snapshot-supplied ids/names/times verbatim → for ids that equal the current actor reuse the already-resolved identity, else look up (with a per-run cache in insertMany :1408–1423) → feed resolved names/emails into the insert builder's context so `__created_by_name`-style denormalized columns fill correctly.
**Invariant:** THREE traps: (1) optional lookups run on `metaDb`, never the tx-scoped `db` — if the lookup throws inside the transaction it would mark the CURRENT tx aborted in Postgres (aborted-tx poisoning); the catch-degrade ladder makes identity resolution best-effort by design. (2) Snapshot values are IDs but display columns want NAMES — hence the three-way fallback (snapshot id → user lookup → current actor) rather than blind passthrough. (3) In batch restores the same user repeats across records; without the cache this is N extra meta-db queries inside a hot loop.
**Probe:** update.spec.ts :695 pins actor-identity-driven lastModifiedBy snapshots.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "resolveActorIdentity restoreRecordsById actorLookupDb", limit: 5 });
```
## Verdict
Adopt: audit-preserving restores need a three-way identity fallback plus out-of-transaction optional lookups with warn-and-degrade semantics — copy both together.
