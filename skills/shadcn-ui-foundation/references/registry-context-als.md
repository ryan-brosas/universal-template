<!-- capsule-v2 -->
# Registry ALS Context — how do per-invocation auth headers reach deep async fetches without threading parameters?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** When a CLI resolves an item whose *dependencies* need different auth headers, where does the header map live so nested fetches find it — without a global mutable config?

## AsyncLocalStorage store with merge-on-write headers
**Path/Symbol:** `packages/shadcn/src/registry/context.ts:1-65` (`RegistryContext`, `withRegistryContext`, `setRegistryHeaders`, `getRegistryHeadersFromContext`, `getRegistryEnvFromContext`, `clearRegistryContext`).
**Signature:** `withRegistryContext<T>(callback: () => T, options?: { env?: NodeJS.ProcessEnv; onGitHubAuthNotice?: (m: string) => void | Promise<void> }): T`; `setRegistryHeaders(headers: Record<url, Record<header, value>>): void`.
**Data Shape:** Store = `{ headers: Record<string /*url*/, Record<string,string>>, env?, onGitHubAuthNotice? }`. Headers are keyed by exact request URL; the fetcher later asks `getRegistryHeadersFromContext(url)` to build its cache key and request headers.

### Decisive source
```ts
const registryContext = new AsyncLocalStorage<RegistryContext>()
const fallbackContext: RegistryContext = { headers: {} }

export function withRegistryContext<T>(callback: () => T, options = {}): T {
  const parentContext = registryContext.getStore()
  return registryContext.run(
    {
      headers: {},                                   // fresh header map per scope
      env: options.env ?? parentContext?.env,        // but inherit env
      onGitHubAuthNotice: options.onGitHubAuthNotice ?? parentContext?.onGitHubAuthNotice,
    },
    callback
  )
}

export function setRegistryHeaders(headers) {
  const context = registryContext.getStore() ?? fallbackContext
  // Merge new headers with existing ones to preserve headers for nested dependencies
  context.headers = { ...context.headers, ...headers }
}
```

**Flow:** command entry calls `withRegistryContext(fn)` → builder computes URL+headers for each requested item → `setRegistryHeaders({[url]: headers})` registers them → resolver recurses into dependencies, which register MORE urls via merge → each `fetchRegistry` call looks up only its own URL's headers. `getRegistryEnvFromContext(key)` reads injected `env` first (testability seam), falling back to `process.env`.
**Invariant:** Header writes MERGE (`{...existing, ...new}`) so outer items' auth survives nested resolution; a fresh scope starts empty. Two hazards to port consciously: (1) when no ALS store is active, writes mutate the shared module-level `fallbackContext` — cross-invocation leakage in long-lived hosts; (2) `clearRegistryContext()` empties the CURRENT store's headers (validator calls it after dry-run validation).
**Probe:** `packages/shadcn/src/registry/fetcher.test.ts:93-124` — two `withRegistryContext` scopes run CONCURRENTLY, each setting `Authorization: Bearer first|second` for the same URL; both responses echo their own token (ALS isolation + header-hash cache keys). `:265-292` proves per-registry headers override default Accept/User-Agent; `:294-324` proves lowercase header names override too. Runner absent in checkout — pinned by direct test read.
**Coverage:** context.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "registry headers AsyncLocalStorage context", limit: 10 });
```

## Verdict
Adopt ALS-scoped `{url→headers, env}` with merge-on-write whenever deep async pipelines need per-request credentials (Node hosts). Adapt: browser/Deno hosts need a different propagation vehicle (context argument or zone equivalent); consider making the no-store fallback throw instead of mutating a singleton. Omit the GitHub auth-notice callback unless porting interactive credential prompts.
