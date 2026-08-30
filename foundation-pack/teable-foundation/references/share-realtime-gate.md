<!-- capsule-v2 -->
# ShareDB submit gate + transactional op broadcast — how do you run a realtime OT server over SQL, letting only client record edits through and broadcasting ops exactly once per DB commit?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Which submits may enter the OT pipeline, and how are raw ops held until the Prisma transaction that produced them commits?

## Source-tagged submit middleware + CLS-buffered after-commit fan-out
**Path/Symbol:** `apps/nestjs-backend/src/share-db/share-db.service.ts:ShareDbService` (60–231): constructor wiring `this.use('submit', this.onSubmit)` (:71) + `prismaService.bindAfterTransaction(...)` buffer (:72–92); projection bypass prefixes `v2ProjectionOpSourcePrefix = '@@v2-projection:'` / `v2ProjectionSubmitSource` (:22–23); gate `onSubmit` (195–230); adapter `share-db/share-db.adapter.ts:ShareDbAdapter extends ShareDb.DB` (`queryPoll` :170, `commit` :229, `getSnapshotBulk` :280, `getOpsBulk` :528).
**Signature:** `onSubmit(context: ShareDBClass.middleware.SubmitContext, next: (err?) => void): void` — Nest middleware signature on the ShareDB class.
**Data Shape:** ShareDB ops keyed by collection `"<IdPrefix>_<tableId>"`; buffered `IRawOpMap`s + `clearCacheKeys` ride in nestjs-cls request store under `tx.rawOpMaps` / `cls.get('clearCacheKeys')`.

### Decisive source
```ts
const submitSource = context.options?.source ?? context.extra?.source;
if (submitSource === v2ProjectionSubmitSource) return next();   // server-projected: bypass
if (opSource.startsWith(v2ProjectionOpSourcePrefix)) return next();

if (!hasClientStream(context.agent)) return next();             // no live client: nothing to sync

const [docType] = context.collection.split('_');
if (docType !== IdPrefix.Record || !context.op.op) {
  this.realtimeMetrics?.recordOperationError('invalid_doc_type');
  return next(new Error('only record op can be committed'));     // hard gate: records only
}
// constructor — hold ops until the producing transaction commits:
this.prismaService.bindAfterTransaction(async () => {
  const rawOpMaps = this.cls.get('tx.rawOpMaps');
  this.cls.set('tx.rawOpMaps', undefined);
  if (ops.length) {
    await this.updateTableMetaByRawOpMap(rawOpMaps);
    await this.publishOpsMap(rawOpMaps);          // broadcast AFTER commit ⇒ never ghost-echo
    this.eventEmitterService.ops2Event(ops);
  }
  /* then flush clearCacheKeys through performance cache */
});
```

**Flow:** every ShareDB submit passes the gate ladder: v2-projection sources bypass (they ARE the server's own writes) → agents without a client stream pass un-gated → everything else must be a Record doc with a non-empty `op`, else rejected with `invalid_doc_type` metric → accepted writes execute inside the request's Prisma transaction, which stashes raw op maps in CLS instead of publishing → `bindAfterTransaction` drains them post-commit alongside meta updates and cache-key clears. The adapter side supplies snapshots/ops from SQL with version-gap reconstruction so reconnecting clients catch up.
**Invariant:** clients can NEVER see an op for data whose transaction rolled back (buffer-until-commit), and the server's own projected writes loop back through the same pipe without being re-gated (source-tag escape hatch) — remove either half and you get echo loops or phantom broadcasts; only record collections accept client OT ops.
**Probe:** `apps/nestjs-backend/src/share-db/share-db.spec.ts::"serves versioned compute activity snapshots after field-read authorization"` (:75), `::"reconstructs compute activity operation gaps from the latest snapshot"` (:131), `::"reconstructs the first compute activity generation as a create operation"` (:173). Honest caveat: the submit-ladder branches themselves have no dedicated upstream spec (integration-covered via e2e suites); port with your own gate tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "ShareDbService onSubmit bindAfterTransaction rawOpMaps", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt source-tagged submit gating + commit-time op buffering for any OT/realtime layer over transactional storage; adopt the collection-prefix document-type policy. Adapt the tag strings, doc-type allowlist, and CLS mechanism to host; swap ShareDB for yjs/other CRDT keeping the same two invariants. Omit teable's computed-activity snapshot loader unless porting the whole v2 realtime surface.
