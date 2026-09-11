<!-- capsule-v2 -->
# Mocker registry — how are mocked modules registered, keyed, and resolved so that one module URL maps to exactly one mock of a known type?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How does `MockerRegistry` keep the four mock kinds (`manual`/`automock`/`autospy`/`redirect`) addressable by both URL and id, and why can a serialized mock be re-registered but a live instance cannot?

## Dual-key registration with type dispatch
**Path/Symbol:** `packages/mocker/src/registry.ts:MockerRegistry` (class :1–153), `MockedModule` family (:155–338).
**Signature:** `register(type: 'manual'|'automock'|'autospy'|'redirect', raw, id, url, factoryOrRedirect?) => MockedModule` (overloaded :19–53, impl :54–132); `add(mock)` :14; `get(id)`/`getById(id)`/`has(id)`/`delete(id)`/`deleteById(id)` :134–152.
**Data Shape:** two `Map`s — `registryByUrl` keyed by mock `url`, `registryById` keyed by mock `id`. Four module classes each carry `{type, raw, id, url}` (+ `redirect` for redirect, + `factory`/`cache` for manual) with `fromJSON`/`toJSON`. `ManualMockedModule.resolve()` lazily runs `factory`, caches into `this.cache`, and wraps failures in a hoisting-hint error.

### Decisive source
```ts
// register() dispatches on type; object arg = serialized JSON (from worker IPC)
const type = typeof typeOrEvent === 'object' ? typeOrEvent.type : typeOrEvent
if (typeof typeOrEvent === 'object') {
  // live instances are REJECTED — only JSON rehydrates (add() updates instead)
  if (event instanceof AutomockedModule || ...) throw new TypeError(
    `Cannot register a mock that is already defined. Expected a JSON representation from \`MockedModule.toJSON\` ... Use "registry.add()" to update a mock instead.`)
  if (event.type === 'automock') { const m = AutomockedModule.fromJSON(event); this.add(m); return m }
  // ... autospy, redirect likewise; manual JSON is refused (factory can't serialize)
}
// string path: validate raw/url/id are strings, then construct the right class
if (type === 'manual') {
  if (typeof factoryOrRedirect !== 'function') throw new TypeError('[vitest] Manual mocks require a factory function.')
  const mock = new ManualMockedModule(raw, id, url, factoryOrRedirect); this.add(mock); return mock
}
// automock/autospy -> new AutomockedModule|AutospiedModule(raw,id,url); redirect -> new RedirectedModule(raw,id,url,redirect)

// ManualMockedModule.resolve(): lazy + cached, promise-aware, loud hoisting hint
resolve(): T {
  if (this.cache) return this.cache
  let exports; try { exports = this.factory() } catch (err) { throw createHelpfulError(err) }
  if (typeof exports === 'object' && typeof exports?.then === 'function')
    return exports.then(r => { assertValidExports(this.raw, r); return (this.cache = r) }, e => { throw createHelpfulError(e) })
  assertValidExports(this.raw, exports); return (this.cache = exports)
}
```

**Flow:** a mock is created either from a live factory (string-type path) or rehydrated from a worker-sent JSON blob (object path). Both funnel into `add()` which writes BOTH maps so the same module is reachable by `url` (what import resolution asks by) and by `id` (what the registry's `getById`/reporter asks by). Manual mocks resolve lazily on first access and memoize; automock/autospy/redirect are pure descriptors.
**Invariant:** the same `url` can only ever hold ONE mock — `add()` overwrites by url/id, so re-registering a URL replaces the prior mock rather than stacking. Live `MockedModule` instances must never be passed to `register()` (they are rejected) because they carry closures/factories that cannot cross the worker boundary; only the JSON shape rehydrates. Manual factories must return a non-null non-array object (or a promise of one) — `assertValidExports` throws the `Did you mean to return an object with a "default" key?` hint otherwise.
**Probe:** `test/unit/test/mocking/vi-mockObject.test.ts` (public `vi.mockObject` path through `ModuleMocker.mockObject` → `mockObject`), plus `test/e2e/test/public-mocker.test.ts` exercising registry-backed `vi.mock`/`vi.unmock` end-to-end; `test/e2e/fixtures/no-module-runner/test/manual-mock.test.ts` pins manual-factory resolve/`cache` behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "MockerRegistry.register", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-key (url+id) registry with a single `register()` type-dispatch and lazy-cached manual resolve — a portable mock-bookkeeping contract. Adapt the JSON rehydration boundary (it exists because factories can't cross worker IPC; a single-process host can `add()` live instances directly). Omit the `createHelpfulError` hoisting wording and the browser `cleanVersion`/`resolveMockPath` URL normalization — those are Vitest-specific transport details.
