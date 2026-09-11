<!-- capsule-v2 -->
# Runtime mockObject — how does the runtime turn a real module object into a deep automock/autospy WITHOUT executing its bodies, and how are circular references kept consistent?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** What invariants does `mockObject` (the runtime twin of the `automockModule` static rewrite) maintain so a porter gets deep-mocking, prototype sharing, and circular refs right?

## Deep structural mock with ref tracking
**Path/Symbol:** `packages/mocker/src/automocker.ts:mockObject` (:16–181); `RefTracker` (:183–201); `getAllMockableProperties` (:244–282); `collectFunctionProperties` (:296–309).
**Signature:** `mockObject(options: {type:'automock'|'autospy', globalConstructors, createMockInstance}, object, mockExports?) => Record<Key,any>`.
**Data Shape:** walks own+inherited enumerable properties via `getAllMockableProperties` (walks the prototype chain, skips `Object/Function/RegExp.prototype`, re-adds `default` if the module is interop'd). `RefTracker` maps original object → mock id so circular references resolve to the SAME mock. `createMockInstance` is injected (the spy factory); `globalConstructors` are injected (so the walker doesn't depend on ambient globals).

### Decisive source
```ts
// circular refs: if we've seen this value, defer a finalizer that points back at the SAME mock
const refId = refs.getId(value)
if (refId !== undefined) {
  finalizers.push(() => define(newContainer, property, refs.getMockedValue(refId)))
  continue
}
// automock: arrays become []; autospy: arrays are mapped element-wise (objects recursed, fns mocked)
if (Array.isArray(value)) {
  if (options.type === 'automock') define(newContainer, property, [])
  else { const array = value.map(v => { if (v && typeof v === 'object') { const o={}; mockPropertiesOf(v,o); return o }
    if (typeof v === 'function') return createMock(v); return v }); define(newContainer, property, array) }
  continue
}
// functions (and classes) become mocks; autospy keeps originalImplementation + prototype members
const isFunction = type.includes('Function') && typeof value === 'function'
if (isFunction) {
  const mock = createMock(newContainer[property])   // createMock passes prototypeMembers + originalImplementation
  newContainer[property] = mock
}
refs.track(value, newContainer[property])
mockPropertiesOf(value, newContainer[property])       // recurse into the mock
// getters: automock replaces get/set with no-ops; autospy copies the descriptor
if (!isModule && descriptor.get) {
  if (options.type === 'autospy') Object.defineProperty(newContainer, property, descriptor)
  else Object.defineProperty(newContainer, property, { configurable, enumerable, get: () => {}, set: descriptor.set ? () => {} : undefined })
}
```

**Flow:** `mockPropertiesOf(object, mockExports)` walks each mockable property: skip readonly props (`arguments`/`caller`/`name`/`length` on functions, `source`/`global`/etc. on RegExp); handle getters (automock → no-op get/set, autospy → copy descriptor); arrays (automock → `[]`, autospy → element-wise recurse); functions/classes → `createMock` (which collects `prototypeMembers` and, for autospy, keeps `originalImplementation`); plain objects → recurse. `RefTracker` dedupes circular references so both ends point at one mock. After the walk, `finalizers` run to plug circular back-references.
**Invariant:** automock and autospy differ ONLY in (a) whether `originalImplementation`/`keepMembersImplementation` is passed to `createMock` and (b) array/getter handling — everything else (recursion, ref tracking, prototype walking) is shared. A class's `prototype` is walked via `collectFunctionProperties`, so instance methods and `Class.prototype.method` share ONE mock state (probe below). Read-only function props are never mocked. `mockExports` (the third arg) is the container written into — this is how `automockModule`'s emitted `__vitest_current_es_module__` gets its mocked surface.
**Probe:** `test/unit/test/mocking/vi-mockObject.test.ts` — `'instance methods and prototype method share the state'` (:88–121) pins that `t1.method.mock` equals `Class.prototype.method.mock` and calls accumulate on the prototype; `'the array is empty by default'` (:186–191) pins automock array→`[]`; `'the array is not empty when spying'` (:193–221) pins autospy element-wise recursion. `test/unit/test/mocking/automocking-class-inheritance.test.ts` (:43–57) pins that `vi.mockObject(class Zoo extends Bar {...})` mocks inherited `doSomething` AND own `ownMethod` (prototype-chain walk).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "mockObject automocker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the deep structural walk with injected `createMockInstance`/`globalConstructors`, the automock-vs-autospy twin semantics, prototype-chain property collection, and ref-tracked circular resolution — a portable runtime mocking kernel. Adapt `createMockInstance` to your spy factory and `globalConstructors` to your host's globals. Omit the `Module`-namespace special-casing (`export * as ns`) unless you need namespace-object recursion.
