<!-- capsule-v2 -->
# Fixture use()-suspension teardown — how does an async fixture keep its value alive until test end and run cleanup in exact reverse order, even when the fixture is a checkpointed aroundEach?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** How is the `({ x }, use) => {...}` protocol implemented with promises so setup errors, missing `use()`, and partial-cleanup checkpoints all behave correctly?

## resolveFixtureFunction + cleanupFnArray checkpoints
**Path/Symbol:** `packages/vitest/src/runtime/runner/fixture.ts` — `resolveFixtureFunction` (:499–552), `callFixtureCleanup` (:245–251), `getFixtureCleanupCount` (:257–259), `callFixtureCleanupFrom` (:266–279), scoped caching `resolveScopeFixtureValue` (:458–497).
**Signature:** `resolveFixtureFunction(fixtureFn, fixtureName, context, cleanupFnArray): Promise<unknown>`; `callFixtureCleanupFrom(context: object, fromIndex: number): Promise<void>`.
**Data Shape:** `cleanupFnArrayMap: WeakMap<contextObject, Array<() => void|Promise<void>>>` — per-context LIFO stack. Fixture fn contract: `(context, use: (value) => Promise<void>) => Promise<void>`. Scoped (file/worker) fixtures cache their VALUE on the shared context and in-flight PROMISE in `scopedFixturePromiseCache: WeakMap<TestFixtureItem, Promise>`.

### Decisive source
```ts
const fixtureReturn = fixtureFn(context, async (useFnArg: unknown) => {
  isUseFnArgResolved = true
  useFnArgPromise.resolve(useFnArg)          // value escapes to the test immediately

  const useReturnPromise = createDefer<void>()
  cleanupFnArray.push(async () => {
    useReturnPromise.resolve()               // 1) release the fixture body past await use()
    await fixtureReturn                      // 2) wait for its post-use code to finish
  })
  await useReturnPromise                     // fixture body SUSPENDS here until cleanup time
}).then(() => {
  if (!isUseFnArgResolved) {                 // returned without use() => loud error w/ registration stack
    const error = new Error(`Fixture "${fixtureName}" returned without calling "use". ...`)
    if (stackTraceError?.stack) error.stack = error.message + stackTraceError.stack.replace(stackTraceError.message, '')
    useFnArgPromise.reject(error)
  }
}).catch((e) => {
  if (!isUseFnArgResolved) { useFnArgPromise.reject(e); return }  // SETUP error = test failure
  throw e                                    // TEARDOWN error must NOT be swallowed
})

// checkpointed cleanup: only fixtures added AFTER fromIndex are torn down,
// and truncation preserves earlier entries — this is how aroundEach cleans
// its own fixtures while leaving per-test fixtures untouched.
const toCleanup = cleanupFnArray.slice(fromIndex)
for (const cleanup of toCleanup.reverse()) await cleanup()
cleanupFnArray.length = fromIndex
```

**Flow:** resolution awaits ONLY the `use(value)` argument (setup completes, value delivered) → fixture body parks inside `await useReturnPromise` → at context teardown, cleanup callbacks run in REVERSE push order; each resolves one fixture's parked promise then awaits its body completion → checkpoint variant (`fromIndex`) tears down just the tail slice and shrinks the array so surrounding scopes' cleanups stay queued. File/worker-scoped fixtures resolve once per shared context: value memoized on the context object, concurrent first-access deduped by the promise cache.
**Invariant:** teardown order is exactly reverse-registration order ACROSS the whole context (not per-fixture nesting) — batching them into nested try/finally would change interleaving with other cleanup sources. Setup-vs-teardown error routing hinges on the `isUseFnArgResolved` flag: before `use`, reject the awaited promise (test fails); after `use`, rethrow asynchronously (must reach unhandled/cleanup reporting). The single-use enforcement lives in `use` being called once per resolution — a fixture that never calls `use` hangs forever unless the `.then()` guard converts it into the explicit error.
**Probe:** `test/e2e/test/scoped-fixtures.test.ts` 'fixture returned without calling use' (:58) pins the loud-error path; worker-scope init/teardown log ordering `'init worker | test1 | teardown worker'` (:162–165) pins suspension semantics; `test/unit/test/fixtures/` + around-hooks tests pin the checkpoint split (`callFixtureCleanupFrom` exists solely for aroundEach's runTest boundary — see pass-1 `around-hooks.md`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "resolveFixtureFunction", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the deferred-use suspension pattern + reverse-order checkpointed cleanup stack for any resource lifecycle tied to test bodies (works far beyond fixtures). Adapt error-routing policy to your host's unhandled-rejection story. Omit the scoped promise cache if your host has no file/worker-shared contexts.
