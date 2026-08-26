<!-- capsule-v2 -->
# Header deletion via set-null — why `deleteHeader` must use `set(name, null)` not `delete()`

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How do you honor a pre-request script's "remove this header" (e.g. strip User-Agent) when axios re-adds its defaults?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/network/axios-instance.ts:makeAxiosInstance` (:44-99, request interceptor :52-77); `__headersToDelete` side-channel stamped by the script runtime.
**Signature:** `makeAxiosInstance(customRequestConfig?) → AxiosInstance` (base: `proxy:false`, keepAlive agents, JSON-string passthrough transformRequest).
**Data Shape:** `config.__headersToDelete?: string[]` travels on the axios config from script land; consumed and deleted in the request interceptor.

### Decisive source
```ts
// Using set(name, null) rather than delete(): the axios http adapter guards its
// own defaults (User-Agent, Accept-Encoding) with set(..., false) which only
// skips writing when the key already exists. delete() removes the key entirely,
// so the guard misses and the adapter re-adds the default. null keeps the key
// present (blocking the guard) while toJSON() omits null values from the wire.
config.headers.set(headerName, null);
```

**Flow:** interceptor reads `__headersToDelete` → skips `host`/`connection` (transport-controlled, deleting breaks chunking/routing) → `headers.set(name, null)` for each → removes the side-channel key so it never reaches adapters. Response interceptor stamps `responseTime = Date.now() - config.startTime`.
**Invariant:** null-set is the load-bearing trick — axios's default-suppression guard checks EXISTENCE (`set(..., false)` no-ops if present), so a deleted key lets defaults back on the wire; host/connection are protected names; timing starts at interceptor time (post-preparation), not at axios.create.
**Probe:** behavior exercised via `packages/bruno-requests/src/network/sent-headers.spec.ts` round-trip + scripting specs; direct unit spec for the interceptor itself absent (coverage caveat recorded).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "makeAxiosInstance headersToDelete", limit: 5 });
```

## Verdict
Adopt set-null suppression + protected transport headers. Adapt to your HTTP client's default-merge semantics (the mechanism differs, the invariant — suppressed keys must still exist as tombstones — does not). Coverage caveat: no dedicated spec file for axios-instance.ts.
