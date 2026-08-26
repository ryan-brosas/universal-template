<!-- capsule-v2 -->
# Native manual-mock cycle protocol — how does module.registerHooks mocking survive a mock factory that imports the very module it mocks (and why is Windows different)?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** When the mocked module's factory awaits `importOriginal()` of itself, what breaks the infinite regress without breaking real circular imports?

## Factory-promise cycle break
**Path/Symbol:** `packages/vitest/src/runtime/moduleRunner/nativeModuleMocker.ts:NativeModuleMocker.getFactoryModule` (:186–222), `checkCircularManualMock` (:169–179), `originalModulePromises`/`factoryPromises`/`processedModules` (:167–182).
**Signature:** `getFactoryModule(id: string): any`; `checkCircularManualMock(url: string): void`.
**Data Shape:** three per-id maps: `processedModules: Map<id, count>` (transform counter), `originalModulePromises: Map<id, DeferPromise>` (resolves `{ __factoryPromise }`), `factoryPromises: Map<id, Promise>` (the user factory run). Manual mocks are reified as generated ESM source (`createManualModuleSource`) whose default export resolves to the factory result.

### Decisive source
```ts
const mockResult = mock.resolve()
if (mockResult instanceof Promise) {
  // to avoid circular dependency, we resolve this function as {__factoryPromise}
  // in `checkCircularManualMock` when it's requested the second time.
  const promise = createDefer()
  promise.finally(() => { this.originalModulePromises.delete(id) })
  mockResult.then(promise.resolve, promise.reject).finally(() => {
    this.factoryPromises.delete(id)
  })
  this.factoryPromises.set(id, mockResult)
  this.originalModulePromises.set(id, promise)
  // Node.js on windows processes all the files first, and then runs them,
  // unlike ... Mac and Unix ... So on Linux/Mac this `if` won't be hit ...
  if ((this.processedModules.get(id) ?? 0) > 1) {
    this.processedModules.set(id, (this.processedModules.get(id) ?? 1) - 1)
    promise.resolve({ __factoryPromise: mockResult })
  }
  return promise   // exports are exposed as `undefined`, later redefined when resolved
}
```

**Flow:** first load of a manually-mocked file → transform counted → generated module source returned; factory starts → factory calls `importOriginal()` (self) → resolver re-enters the same id → `checkCircularManualMock` sees `originalModulePromises.has(id)` and resolves the ORIGINAL-module defer with `{ __factoryPromise }` — so the original's export for the factory binding becomes a placeholder that later unwraps to the factory result → factory completes → its exports redefine over the placeholder. On Windows, load/eval ordering means the re-entry never happens during evaluation, so `getFactoryModule` pre-resolves using the transform COUNT (>1) instead. Both ladders converge on `{ __factoryPromise }`.
**Invariant:** the cycle must break at exactly ONE point with a sentinel object (`{ __factoryPromise }`) rather than awaiting — awaiting either side deadlocks. The count decrement makes the escape hatch single-shot per extra transform. Node's per-platform load/evaluate interleaving is part of the protocol, not an implementation detail: dropping the processedModules branch regresses Windows only.
**Probe:** `test/e2e/fixtures/no-module-runner/test/manual-mock.test.ts` — `vi.mock(import('../src/index.ts'), async (importOriginal) => …)` carries the comment "doesn't hang even though it's circular!" and asserts all exports incl. pass-through `helloMe`; suite gated `describe.runIf(module.registerHooks)` in `test/e2e/test/no-module-runner.test.ts`. Coverage caveat: no unit test isolates getFactoryModule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "NativeModuleMocker getFactoryModule checkCircularManualMock originalModulePromises", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-ladder cycle break (re-entry sentinel + platform-specific count fallback) whenever a mock layer can intercept its own dependency's resolution. Adapt map lifetimes to your registry reset semantics (`reset()` clears registries but NOT these maps). Omit the builtin-manual-mock path unless your host mocks node builtins through native hooks.
