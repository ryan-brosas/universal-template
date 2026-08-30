<!-- capsule-v2 -->
# Cross-Runtime TS SDK Primitives — how does one SDK source tree run on Node, Bun, Deno, and edge?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What are the minimal primitives that make a fetch-based SDK portable across JS runtimes without `any` casts leaking everywhere?

## Typed env shim + timeout-owned fetch wrapper
**Path/Symbol:** `packages/typescript-sdk/src/internal/env.ts` — `envVar` (:19–22); `internal/fetch.ts` — `fetchWithTimeout` (:15–31).
**Signature:** `envVar(name: string): string | undefined`; `fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number, serverOrigin: string): Promise<Response>`.
**Data Shape:** env shim narrows via `interface EnvHost { process?: { env?: Record<string, string | undefined> } }` cast of globalThis; fetch wrapper maps ANY transport failure to `ServerUnreachableError(serverOrigin, cause)`.

### Decisive source
```ts
// fetch.ts
const controller = new AbortController();
const timer = setTimeout(() => controller.abort(), timeoutMs);
try {
    return await fetch(url, { ...init, signal: controller.signal });
} catch (err) {
    throw new ServerUnreachableError(serverOrigin, err);
} finally {
    clearTimeout(timer);
}
```

**Flow:** entry points resolve config: `envVar("AWAITHUMANS_URL") ?? envVar("AWAITHUMANS_ADMIN_API_TOKEN")` (await-human.ts :88/:99 — pure function, no caching, called only at SDK entry) → call sites pass HTTP intent only; status-code handling stays with the CALLER ("different routes map non-2xx to different SDK errors").
**Invariant:** the timer is cleared in `finally` even on throw; abort ⇒ catch ⇒ typed unreachable error (never a raw AbortError leak); `globalThis.process` is typed `undefined` by DOM lib so the typed shim replaces scattered `any` casts; adapters deliberately do NOT reuse this helper (langgraph's `createTaskOnServer` uses bare fetch because nodes can't reach env vars — serverUrl is a required option there).
**Probe:** no dedicated upstream unit test for these two helpers (transport exercised indirectly via await-human tests with a live server) — coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "fetchWithTimeout envVar ServerUnreachableError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt both primitives verbatim for any cross-runtime SDK. Adapt error type and timeout policy per route family. Omit the shim only if you target Node exclusively.
