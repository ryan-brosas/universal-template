<!-- capsule-v2 -->
# upgrade-cursor-metadata-adapter

## Source
- Repo: `twenty-crm`
- Path: `packages/twenty-server/src/engine/twenty-orm/upgrade-aware/upgrade-aware-entity-metadata.adapter.ts` (+ `upgrade-aware-repository-state.ts`, `install-upgrade-aware-repository-proxy.ts`)
- Symbol: `UpgradeAwareEntityMetadataAdapter` / `UpgradeAwareRepositoryState` / `installUpgradeAwareRepositoryProxy`
- Lines: adapter 36-77 (init/refresh), 79-91 (public queries), 93-130 (snapshots), 132-186 (cursor application); state file 1-37 whole; install file 12-83 whole
- Commit: `a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0`
- Graph Node: `ext-twenty-crm.packages.twenty-server.src.engine.twenty-orm.upgrade-aware.upgrade-aware-entity-metadata.adapter.UpgradeAwareEntityMetadataAdapter`

## Signature & Data Shape
```typescript
type EntityMetadataSnapshot = {
  tableName: string;
  tablePath: string;
  givenTableName: string | undefined;
  canonicalColumns: ReadonlyArray<ColumnMetadata>;
  columnDatabaseNamesByPropertyName: ReadonlyMap<string, string>;
  columnSelectByPropertyName: ReadonlyMap<string, boolean>;
  columnInsertByPropertyName: ReadonlyMap<string, boolean>;
  columnUpdateByPropertyName: ReadonlyMap<string, boolean>;
};

@Injectable()
export class UpgradeAwareEntityMetadataAdapter implements OnModuleInit {
  onModuleInit(): Promise<void>;
  refresh(): Promise<void>;
  isEntityAvailable(entityClass: Function): boolean;
  getHiddenColumnPropertyNames(entityClass: Function): ReadonlySet<string>;
}
```

## Decisive Source Excerpt
```typescript
// onModuleInit — bootstrap order is load-bearing:
this.validateDecoratorsAgainstSequence();   // @WasIntroducedInUpgrade names MUST exist in sequence
this.captureCanonicalSnapshots();           // WeakMap<EntityMetadata, snapshot> BEFORE mutation
this.currentCursor = sequence.length;
this.applyCursorToMetadata();               // mutate TypeORM metadata to end-of-sequence state
UpgradeAwareRepositoryState.getInstance().setMetadataService(this);
try { await this.refresh(); } catch (error) { /* core.upgradeMigration not readable yet → skip */ }

// refresh — cursor derivation from the DB's own progress record:
if (!isDefined(lastAttempted)) nextCursor = 0;
else {
  const index = this.stepNameToIndex.get(lastAttempted.name);
  if (!isDefined(index)) nextCursor = 0;
  else nextCursor = lastAttempted.status === 'completed' ? index + 1 : index;
}
if (nextCursor === this.currentCursor) return;   // idempotent re-entry

// buildIsStepAppliedPredicate:
return index < this.currentCursor;   // a step counts as applied only when FULLY passed
```

## Flow
1. **Snapshot-then-mutate**: canonical entity shapes are captured into WeakMaps keyed by TypeORM's live `EntityMetadata` objects BEFORE any cursor is applied — later code can always compute both "shape at cursor" and "canonical shape".
2. The adapter boots the metadata to `currentCursor = sequence.length` (fully upgraded) because a freshly booting node must see the FINAL schema; `refresh()` then rewinds to the position recorded in `core.upgradeMigration` (`lastAttempted` + status). A half-applied step leaves the cursor AT that step's index (not past it), so its entities stay unavailable.
3. `applyCursorToMetadata` walks every entity: entities introduced by unapplied steps become unavailable and get their columns hidden/renamed per `resolveEntityShapeAtUpgradeCursor`; counters (renamed/unavailable/hiddenColumns) are logged once per pass.
4. `UpgradeAwareRepositoryState` is a process-wide singleton with **fail-open defaults**: no metadata service ⇒ everything available, zero hidden columns. The proxy layer consults it on EVERY repository call.
5. `installUpgradeAwareRepositoryProxy(dataSource)` monkey-patches BOTH `dataSource.getRepository` AND `EntityManager.prototype.getRepository` (prototype-level so transaction-scoped managers are covered) with a module-level `WeakMap` wrapper cache; managers on OTHER connections pass through untouched (`this.connection !== dataSource` guard).

## Invariant
The availability truth flows ONE direction: upgrade sequence + DB progress row → adapter cursor → singleton state → repository proxy behavior. Snapshots precede mutation, decorator names are validated against the sequence at boot, cursor moves are idempotent (`nextCursor === currentCursor` early-return), and an unreadable migration table during first boot degrades to "everything available" rather than blocking startup.

## Direct-Test Probe
```bash
grep -n "setMetadataService\|captureCanonicalSnapshots\|nextCursor = lastAttempted.status" packages/twenty-server/src/engine/twenty-orm/upgrade-aware/upgrade-aware-entity-metadata.adapter.ts   # => :71,:72,:99
grep -n "isDefined(this.metadataService)" packages/twenty-server/src/engine/twenty-orm/upgrade-aware/upgrade-aware-repository-state.ts   # => :24 fail-open default
grep -n "entityManagerPrototype.getRepository\|wrappedRepositoryCache" packages/twenty-server/src/engine/twenty-orm/upgrade-aware/install-upgrade-aware-repository-proxy.ts   # => :55,:13
```
Integration coverage rides the sibling spec `__tests__/upgrade-aware-entity-metadata.adapter.spec.ts` and the proxy spec (:61 `await adapter.onModuleInit()` inside the proxy harness).

## Graph Query
```bash
echo '{"project":"ext-twenty-crm","name_pattern":"UpgradeAwareEntityMetadataAdapter"}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt for any app that must boot new code against a database still mid-migration. The snapshot-before-mutate discipline plus the prototype-level manager patching are the two pieces porters skip and then wonder why transactional repositories bypass their guards.
