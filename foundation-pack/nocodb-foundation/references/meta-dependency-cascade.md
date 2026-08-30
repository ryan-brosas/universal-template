<!-- capsule-v2 -->
# meta-dependency cascade — when a column/filter/hook/view dies, how do dependents get repaired in one transaction without re-triggering the dispatcher?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the dispatch contract that lets N independent handlers react to one meta event — and what stops infinite recursion and partial repairs?

## Boot-registered handler map + suppression-flag recursion guard + lazy shared transaction

**Path/Symbol:** `packages/nocodb/src/services/meta-dependency/event-handler.service.ts:MetaDependencyEventHandler` (:14–100); provider `meta-dependency.provider.ts` (:41L) supplies handler classes under `META_DEPENDENCY_MODULE_PROVIDER_KEY`; handlers implement `triggerMetaEvents` / `getAffectedDependency` / `handle` (16 handlers under `handler/column/*` + `handler/hook/hook-delete-button-ref-dependency.handler.ts`).
**Signature:** `handleEvent(context: NcContext, param: MetaDependencyEventRequest, ncMeta = Noco.ncMeta): Promise<void>`; registry `metaEventHandlerMap: Record<MetaEventType, MetaEventHandler[]>`.
**Data Shape:** Ten event types seeded at :29–40 (COLUMN_ADDED/DELETED/UPDATED, HOOK_DELETED, FILTER_CREATED/UPDATED/DELETED, VIEW_UPDATED/DELETED, TABLE_DELETED) — every key pre-seeded to an empty array so handler lookups never hit undefined.

### Decisive source
```ts
// :65-83 — suppression + lazy transaction
if (context.suppressDependencyEvaluation) return;
// next context will have suppressDependencyEvaluation as true by default unless modules override it.
const nextContext = { ...context, suppressDependencyEvaluation: true } as NcContext;
...
const affectedDependencies = await handler.getAffectedDependency(nextContext, param, trxNcMeta ?? ncMeta);
if (affectedDependencies) {
  trxNcMeta = trxNcMeta ?? (await ncMeta.startTransaction());
  await handler.handle(nextContext, {...param, affectedDependencyResult: affectedDependencies}, trxNcMeta);
}
```

**Flow:** onModuleInit resolves each injected handler class via `moduleRef.get(cls, {strict:false})` and registers it under EVERY type its `triggerMetaEvents` lists (skipping invalid handlers with a logged error rather than crashing boot) → on event: bail if suppressed → clone context with suppression FORCED ON for all downstream work → per registered handler in order: `getAffectedDependency` decides relevance; ONLY a non-null result opens (or reuses) the SHARED transaction and runs `handle` → commit once after all handlers, rollback+rethrow on any failure. The transaction is LAZY: if no handler finds affected dependencies, no transaction is ever opened. Handler-side repair semantics live in the 16 handlers (e.g. column-delete-filter removes filters referencing the column; column-delete-transitive-dependents walks transitive closure :405L).
**Invariant:** (1) The suppression flag is THE recursion guard: any meta write performed INSIDE a handler emits further meta events whose dispatch sees suppress=true and stops — a porter who clears the flag inside a handler creates unbounded cascades. (2) All handlers share ONE transaction so a mid-cascade failure rolls back EVERY repair atomically; giving each handler its own tx leaves half-repaired metadata on failure. (3) Registration validates `Array.isArray(each.triggerMetaEvents)` defensively because EE builds can contribute handlers that CE builds instantiate differently.

### Porting traps (each verified against source)
- `getAffectedDependency` receives `trxNcMeta ?? ncMeta` — the FIRST relevant handler's probe may run OUTSIDE the not-yet-opened transaction; only subsequent work is transactional. Porters needing read-your-writes across probes must open the tx eagerly instead.
- In-file anchors: `grep -c 'suppressDependencyEvaluation' src/services/meta-dependency/event-handler.service.ts` → 3 (check, clone, comment); `grep -c 'startTransaction' …` → 1; `grep -n 'strict: false' …` → :24.

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -n 'suppressDependencyEvaluation: true' src/services/meta-dependency/event-handler.service.ts | cut -d: -f1` → `72` and `sed -n '77,93p' src/services/meta-dependency/event-handler.service.ts | grep -c 'trxNcMeta ??'` → `2` (probe site :80 + tx-open :83).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "MetaDependencyEventHandler handleEvent suppressDependencyEvaluation getAffectedDependency", limit: 10 });
```
Resolves `handleEvent` :60-99 rank-1 plus concrete handlers (`ColumnTimezoneUpdateDependencyHandler.getAffectedDependency` :23-63 rank-2).

## Verdict
Adopt the pre-seeded event map, forced-suppression next-context, lazy shared transaction, and boot-time moduleRef registration; adapt the MetaEventType union to host; omit NestJS DI specifics. Coverage caveat: no direct tests at pin; probes are source-greps.
