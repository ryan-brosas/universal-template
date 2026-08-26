<!-- capsule-v2 -->
# Fixture registration graph — how do fixture scopes, overrides, and dependency validation form a per-suite lattice that never mutates a parent's registrations?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** How are fixtures parsed, scoped (test/file/worker), overridden per describe, and validated so resolution order and inheritance behave identically after porting?

## TestFixtures.parseUserFixtures / override / scope lattice
**Path/Symbol:** `packages/vitest/src/runtime/runner/fixture.ts:TestFixtures` — `extend` (:63–68), `get(suite)` closest-override walk (:70–84), `override` (:86–102), `parseUserFixtures` (:118–237), vmThreads downgrade (:201–203).
**Signature:** `extend(runner, userFixtures): TestFixtures` (immutable); `override(runner, userFixtures): void`; `parseUserFixtures(runner, userFixtures, supportNonTest, registrations?): FixtureRegistrations`.
**Data Shape:** `TestFixtureItem = { name, value, auto, injected, scope: 'test'|'file'|'worker', deps: Set<string>, parent?: TestFixtureItem }`. `FixtureRegistrations = Map<string, TestFixtureItem>`. `_overrides: WeakMap<Suite, FixtureRegistrations>` holds per-suite copies. Option keys that identify a `[fn, options]` tuple: `auto/injected/scope`.

### Decisive source
```ts
// override NEVER mutates the parent map — it copies the closest chain first
const suiteRegistrations = new Map(this.get(suite))     // closest override or base
const registrations = this.parseUserFixtures(runner, userFixtures, isTopLevel, suiteRegistrations)
if (isTopLevel) this._registrations = registrations
else this._overrides.set(suite, registrations)

// re-declaration inherits options but must not change them
const parent = registrations.get(name)
if (parent && options) {
  if (parent.scope !== options.scope)
    errors.push(new FixtureDependencyError(`The "${name}" fixture was already registered with a "${options.scope}" scope.`))
  if (parent.auto !== options.auto)
    errors.push(new FixtureDependencyError(`The "${name}" fixture was already registered as { auto: ${options.auto} }.`))
}

// self-reference is legal ONLY with a base implementation ({ a: ({ a }) => ... })
if (depName === fixture.name && !fixture.parent)
  errors.push(new FixtureDependencyError(`The "${fixture.name}" fixture depends on itself, but does not have a base implementation.`))

// scope lattice: test ⊃ file ⊃ worker by array index order
if (TestFixtures._fixtureScopes.indexOf(fixture.scope) > TestFixtures._fixtureScopes.indexOf(dep.scope))
  errors.push(new FixtureDependencyError(`The ${fixture.scope} "${fixture.name}" fixture cannot depend on a ${dep.scope} fixture "${dep.name}".`))

// worker scope degrades to file under VM pools (workers are per-test there)
if (item.scope === 'worker' && (runner.pool === 'vmThreads' || runner.pool === 'vmForks'))
  item.scope = 'file'
```

**Flow:** `test.extend({...})` at file top-level → `extend()` parses + returns a NEW immutable TestFixtures → inside `describe`, `.extend(...)` chains again; `override()` (suite-level override API) copies the closest chain and stores per-suite → resolution walks `get(suite)` up the suite chain for the nearest override map, else base `_registrations` → all validation errors accumulate into ONE throw (`AggregateError`) so users see every problem at once.
**Invariant:** registration maps are copy-on-write — a child override MUST NOT mutate the map it inherited from (mutating would leak overrides into sibling suites). Scope rules: non-top-level definitions may only be `scope: 'test'`; a fixture can only depend on equal-or-wider scope; unknown deps and option-changing redeclarations are build-time throws. The `parent` pointer doubles as the "use base implementation" link AND the cycle-escape hatch during resolution.
**Probe:** `test/unit/test/fixture-initialization.test.ts` (override + dependency describes :51–154), `test/unit/test/fixture-options.test.ts` (:6–19 `[fn, {auto:true}]` tuple parse; auto runs once per :23–35), `test/e2e/test/scoped-fixtures.test.ts` ('test fixture cannot import from file fixture' :24, worker-scope init/teardown ordering :134–165).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "TestFixtures.override", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the copy-on-write registration lattice + scope-order validation for any fixture/DI-style context system. Adapt the destructuring-based dep extraction host rules (see fixture-use-suspension capsule). Omit the `injected` option unless your host has framework-provided fixture values.
