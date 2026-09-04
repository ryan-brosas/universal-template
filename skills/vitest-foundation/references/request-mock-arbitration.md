<!-- capsule-v2 -->
# Request-layer mock arbitration — at the moment a module request executes, which of stale-mock bypass, self-import detection, automock freshness, and cycle fall-through wins?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** Given a resolved module node carrying a `mockedModule` marker, what is the exact decision ladder before its exports are evaluated?

## Arbitration ladder in cachedRequest
**Path/Symbol:** `packages/vitest/src/runtime/moduleRunner/moduleRunner.ts:cachedRequest` (:160–206 region — meta check :167, stale bypass :171–177, self-import :178–184, automock freshness :185–191, string/object settle :199–205).
**Signature:** `requestWithMockedModule(url: string, evaluatedNode: EvaluatedModuleNode, callstack: string[], mock: MockedModule): Promise<any>`; `mockedRequest(url, node, callstack): Promise<any | undefined>`.
**Data Shape:** the resolution layer stamps `mod.meta.mockedModule` (a `MockedModule` from the registry) onto the module node; `callstack: string[]` carries ids/urls/redirects currently being requested. `requestWithMockedModule` returns exports objects OR a redirect URL STRING; `mockedRequest` returns `undefined` when no mock is registered.

### Decisive source
```ts
const currentMock = this.mocker.getDependencyMock(mod.id)
if (!currentMock) {                       // 1. stale marker (doUnmock removed it)
  const node = await this.fetchModule(injectQuery(url, '_vitest_original'))
  return this._cachedRequest(node.url, node, callstack, metadata)   // force actual
}
const isSelfImport = callstack.includes(mockId)
  || callstack.includes(url)
  || ('redirect' in currentMock && callstack.includes(currentMock.redirect))
if (isSelfImport) { /* fetch _vitest_original twin → actual */ }     // 2. factory imports its target
const isAutoMock = currentMock.type === 'automock' || currentMock.type === 'autospy'
if (isAutoMock && currentMock !== mockedModule) {                    // 3. re-registered mock
  const freshNode = await this.fetchModule(injectQuery(url, '_vitest_original'))
  mocked = await this.mocker.requestWithMockedModule(url, freshNode, callstack, currentMock)
}
...
if (typeof mocked === 'string') {         // redirect: string result = url to fetch
  const node = await this.fetchModule(mocked); return this._cachedRequest(mocked, node, ...)
}
if (mocked != null && typeof mocked === 'object') return mocked       // exports
return this._cachedRequest(url, mod, callstack, metadata)             // 4. fall-through = cycle
```

**Flow:** request arrives with a stamped mock marker → registry is RE-QUERIED by id (`getDependencyMock`) and wins over the stale marker → missing ⇒ bypass via `_vitest_original` query twin → self-import (callstack contains mock id, url, or redirect target) ⇒ same bypass → auto-mocks whose identity CHANGED since stamping get re-automocked over a FRESH original fetch (doMock after import) → manual mocks resolve through the factory cache with callstack push/pop around the await; redirect type RETURNS its target as a string for the outer layer to fetch. Any path returning `null`/`undefined` falls through to real evaluation — which is precisely how an original module mid-cycle evaluates.
**Invariant:** the REGISTRY, not the stamped meta, is live truth; every bypass must fetch the `_vitest_original` query twin or the resolver would re-enter the mock. Identity comparison (`currentMock !== mockedModule`) is by object reference — re-registration must produce a NEW registry entry to be seen. The string-vs-object return duality is load-bearing: strings are deferred redirects, objects are final exports.
**Probe:** `test/e2e/fixtures/no-module-runner/test/manual-mock.test.ts` ("importMock works" asserts redirect-to-`__mocks__` even without vi.mock + automock fallbacks); `test/e2e/test/mocking.test.ts:266/:307` do-not-load cases prove unmocked originals never evaluate. Coverage caveat: ladder order itself has no isolated unit test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "requestWithMockedModule mockedRequest mockedModule callstack self-import", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-step arbitration order (stale → self-import → freshness → cycle fall-through) for any loader-level mock interception. Adapt the marker transport (`meta.mockedModule` vs your loader's annotation). Omit the OTel span inside `requestWithMockedModule` unless tracing is required.
