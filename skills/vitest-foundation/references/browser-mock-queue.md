<!-- capsule-v2 -->
# Browser mock registration queue — how do async vi.mock registrations in the browser become safe before ANY dynamic import touches the mocked module, and how does unmock/invalidate unwind?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** What is the queue/prepare/registry protocol that keeps browser-mode mocks race-free across `queueMock`, dynamic imports, and resets?

## ModuleMocker queue + wrapDynamicImport
**Path/Symbol:** `packages/mocker/src/browser/mocker.ts:ModuleMocker` — `queue`/`mockedIds` (:14–15), `prepare` (:24–29), `queueMock` (:170–214), `queueUnmock` (:216–232), `wrapDynamicImport` (:236–246), `invalidate` (:51–59), `importActual` (:61–82).
**Signature:** `public queueMock(rawId: string, importer: string, factoryOrOptions?: ModuleMockOptions | (() => any)): void`; `public wrapDynamicImport<T>(moduleFactory: () => Promise<T>): Promise<T>`.
**Data Shape:** `queue = Set<Promise<void>>` (in-flight registrations), `mockedIds = Set<string>` (for later bulk invalidation), `registry: MockerRegistry` of `MockedModule`s typed `manual | automock | autospy | redirect`, keyed by mockUrl. RPC surface: `{ invalidate(ids), resolveId(id, importer), resolveMock(id, importer, {mock}) }`.

### Decisive source
```ts
// registration is fire-and-forget but ALWAYS tracked; factory interop for
// CJS deps is decided server-side (needsInterop) and applied client-side
const promise = this.rpc.resolveMock(rawId, importer, {
  mock: typeof factoryOrOptions === 'function' ? 'factory' : factoryOrOptions?.spy ? 'spy' : 'auto',
}).then(async ({ redirectUrl, resolvedId, resolvedUrl, needsInterop, mockType }) => {
  ...
  const factory = typeof factoryOrOptions === 'function' ? async () => {
    const data = await factoryOrOptions()
    return needsInterop ? { default: data } : data   // vite wraps externals for interop
  } : undefined
  // priority order matters: manual > autospy > redirect > automock
  if (mockType === 'manual') module = this.registry.register('manual', ...)
  else if (mockType === 'autospy') module = this.registry.register('autospy', ...) // autospy BEATS redirect
  else if (mockType === 'redirect') module = this.registry.register('redirect', ..., mockRedirect!)
  else module = this.registry.register('automock', ...)
  await this.interceptor.register(module)
}).finally(() => { this.queue.delete(promise) })
this.queue.add(promise)

// THE invariant: every user-land dynamic import waits for pending registrations first
public wrapDynamicImport<T>(moduleFactory: () => Promise<T>): Promise<T> {
  const promise = new Promise<T>((resolve, reject) => {
    this.prepare().finally(() => { moduleFactory().then(resolve, reject) })
  })
  return promise
}

public async prepare(): Promise<void> {
  if (!this.queue.size) return
  await Promise.all([...this.queue.values()])
}
```

**Flow:** `vi.mock(...)` in browser → `queueMock` starts the async resolve+register chain and parks it in `queue` → test body's imports are wrapped so each dynamic import FIRST awaits `prepare()` (all queued registrations settle) THEN resolves the module → interceptor serves mocked modules by URL → `queueUnmock` resolves+deletes registry entry + removes from interceptor → `invalidate()` bulk-RPCs the ids, clears interceptor + registry + mockedIds.
**Invariant:** a mock MUST be registered before any import can observe it — the queue+prepare pair is the whole race-safety story; unwrapping dynamic imports breaks mocking non-deterministically under load. Mock-type precedence is encoded once here (`spy:true` never wins over an explicit factory; autospy beats redirect). URL normalization (`resolveMockPath` strips `/@fs/<root>` prefixes; `cleanVersion` drops Vite's `?v=hash`) must match the interceptor's keying EXACTLY or mocks silently miss. `importActual` appends `_vitest_original&ext<ext>` query to bypass interception and re-wraps optimized CJS defaults per Vite's interop helper shape.
**Probe:** `test/unit/test/browserAutomocker.test.ts` pins the automock emission used behind this queue; `test/e2e/test/public-mocker.test.ts` + `test/e2e/test/mocking.test.ts` drive end-to-end mock/actual/unmock behavior through the public API. No unit test isolates `wrapDynamicImport` itself (coverage caveat — cite e2e suites when porting).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "queueMock", limit: 5, fields: ["signature", "name", "file"] });
```
(Graph shows the runtime twin `BareModuleMocker.queueMock` at `runtime/moduleRunner/bareModuleMocker.ts:295` — same contract without RPC.)

## Verdict
Adopt the track-all-registrations + prepare-gate-before-import pattern for ANY environment where mock setup is asynchronous relative to imports. Adapt the RPC split (server resolve vs client register) to your transport. Omit the MSW/native interceptor duality if your host has only one interception mechanism.
