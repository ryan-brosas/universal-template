<!-- capsule-v2 -->
# upgrade-aware-repository-proxy

## Source
- Repo: `twenty-crm`
- Path: `packages/twenty-server/src/engine/twenty-orm/upgrade-aware/upgrade-aware-repository.proxy.ts`
- Symbol: `wrapRepositoryWithUpgradeAwareProxy` / `REPOSITORY_METHOD_BEHAVIORS` / `handleRepositoryMethodCall`
- Lines: 20-100 (behavior table), 247-268 (proxy get trap), 271-333 (call handler)
- Commit: `a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0`
- Graph Node: `ext-twenty-crm.packages.twenty-server.src.engine.twenty-orm.upgrade-aware.upgrade-aware-repository.proxy.wrapRepositoryWithUpgradeAwareProxy`

## Signature & Data Shape
```typescript
type RepositoryMethodBehavior =
  | {
      kind: 'short-circuit-read';
      produceEmpty: (entityClass: Function) => Promise<unknown>;
    }
  | { kind: 'throw-on-unavailable-write' };

export const wrapRepositoryWithUpgradeAwareProxy = <Entity extends object>({
  repository,
  entityClass,
  state,
}: {
  repository: Repository<Entity>;
  entityClass: Function;
  state: UpgradeAwareRepositoryState;
}): Repository<Entity>;
```

## Decisive Source Excerpt
```typescript
const REPOSITORY_METHOD_BEHAVIORS = new Map<string, RepositoryMethodBehavior>([
  ['find',        { kind: 'short-circuit-read', produceEmpty: () => Promise.resolve([]) }],
  ['findBy',      { kind: 'short-circuit-read', produceEmpty: () => Promise.resolve([]) }],
  ['findAndCount',{ kind: 'short-circuit-read', produceEmpty: () => Promise.resolve([[], 0]) }],
  ['findOne',     { kind: 'short-circuit-read', produceEmpty: () => Promise.resolve(null) }],
  ['findOneOrFail', {
    kind: 'short-circuit-read',
    produceEmpty: (entityClass) =>
      Promise.reject(new EntityNotFoundError(entityClass, undefined)),
  }],
  ['count',       { kind: 'short-circuit-read', produceEmpty: () => Promise.resolve(0) }],
  ['exists',      { kind: 'short-circuit-read', produceEmpty: () => Promise.resolve(false) }],
  ['save',    { kind: 'throw-on-unavailable-write' }],
  ['insert',  { kind: 'throw-on-unavailable-write' }],
  ['update',  { kind: 'throw-on-unavailable-write' }],
  ['delete',  { kind: 'throw-on-unavailable-write' }],
  // ... remove, softRemove, recover, upsert, increment, decrement, restore, softDelete
]);

const handleRepositoryMethodCall = <Entity extends object>({ ... }): unknown => {
  if (!state.isEntityAvailable(entityClass)) {
    if (behavior.kind === 'throw-on-unavailable-write') {
      return Promise.reject(
        new UpgradeUnavailableEntityWriteException(entityClass.name, methodName),
      );
    }
    return behavior.produceEmpty(entityClass);
  }

  const rewrittenArgs =
    METHODS_THAT_ACCEPT_FIND_OPTIONS.has(methodName) && args.length > 0
      ? [
          stripUnavailableSelect(
            entityClass,
            state,
            stripUnavailableRelations(target.metadata, state, args[0]),
          ),
          ...args.slice(1),
        ]
      : args;

  return (target[methodName] as unknown as (...callArgs: unknown[]) => unknown).apply(
    target,
    rewrittenArgs,
  );
};
```

## Flow
1. Proxy `get` trap looks up the method name in `REPOSITORY_METHOD_BEHAVIORS`; known methods route through `handleRepositoryMethodCall`, everything else falls through to `Reflect.get` with function `.bind(target)` (class constructors returned unbound).
2. **Entity unavailable** (`state.isEntityAvailable === false`): reads short-circuit to typed empty results — `[]` for find-family, `[[], 0]` for findAndCount, `null` for findOne, `0` for count, `false` for exists, and a **rejected `EntityNotFoundError`** for the `*OrFail` twins (so caller error handling stays truthful). Writes reject with `UpgradeUnavailableEntityWriteException(entityName, method)` — fail-closed.
3. **Entity available**: args[0] of the 12 find-options methods is rewritten BEFORE delegation — `stripUnavailableRelations` first (drops relations whose inverse entity is unavailable), then `stripUnavailableSelect` (removes hidden-column property names from array OR object `select`). Both strippers are no-op-preserving: if nothing was filtered they return the ORIGINAL options object identity.
4. Delegation uses `.apply(target, rewrittenArgs)` so TypeORM's internal `this` binding survives.

## Invariant
Repositories against not-yet-migrated entities must fail closed on ALL writes while reads stay available with deterministic empty structures. Availability filtering extends past the entity itself: find-options referencing unavailable RELATED entities (via `relations`) or hidden columns (`select`) are stripped rather than rejected — partial availability degrades gracefully, never throws on the happy path. `*OrFail` methods must still reject (an empty result IS an error for them) but with the standard `EntityNotFoundError`, not an upgrade-specific one.

## Direct-Test Probe
- File: `packages/twenty-server/src/engine/twenty-orm/upgrade-aware/__tests__/upgrade-aware-repository.proxy.spec.ts`
- Suite: `describe('wrapRepositoryWithUpgradeAwareProxy')` (:23)
- Pins: `it('short-circuits find() to an empty array when the entity is unavailable')` (:24), `it('strips hidden columns from an array select while preserving unknown keys')` (:77), `it('strips hidden columns from an object select while preserving unknown keys')` (:111)

```bash
grep -c "throw-on-unavailable-write" packages/twenty-server/src/engine/twenty-orm/upgrade-aware/upgrade-aware-repository.proxy.ts   # => 12
grep -n "EntityNotFoundError(entityClass, undefined)" packages/twenty-server/src/engine/twenty-orm/upgrade-aware/upgrade-aware-repository.proxy.ts  # => 2 hits (:57,:67 approx)
```

## Graph Query
```bash
echo '{"project":"ext-twenty-crm","name_pattern":"wrapRepositoryWithUpgradeAwareProxy"}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the read-short-circuit / write-fail-closed repository proxy pattern for zero-downtime rolling upgrades, INCLUDING the find-options stripping ladder — a porter who only ports the empty-result table ships broken queries that select/relation-load columns that do not exist yet.
