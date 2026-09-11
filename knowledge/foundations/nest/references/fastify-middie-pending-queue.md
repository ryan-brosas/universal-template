<!-- capsule-v2 -->
# fastify middie pending-queue — why must middleware calls queue when the compat layer is not yet registered?

**Source:** nest MIT `master@4c38a5ab1`; Codebase Memory project `nest`. **Question:** Fastify only supports express-style middleware through the middie plugin, which registers asynchronously at init — what must `use()` do for middleware handed to it BEFORE that registration?

## pendingMiddlewares queue drained in init(), plus lazy per-route registration
**Path/Symbol:** `packages/platform-fastify/adapters/fastify-adapter.ts:765-773 use`, queue field `:168 pendingMiddlewares`, drain `init :313-326`, registration `registerMiddie :847-852`; consumer of the factory `createMiddlewareFactory :691-755`.
**Signature:** `use(...args: any[]): this` (returns `this` while queuing — callers may chain during boot).
**Data Shape:** `pendingMiddlewares: Array<{ args: any[] }>`; `isMiddieRegistered` starts false unless constructor saw `skipMiddie` option (:272-274).

### Decisive source
```ts
// fastify-adapter.ts:765-773
public use(...args: any[]) {
  // Fastify requires @fastify/middie plugin to be registered before middleware can be used.
  // If middie is not registered yet, we queue the middleware and register it later during init.
  if (!this.isMiddieRegistered) {
    this.pendingMiddlewares.push({ args });
    return this;
  }
  return (this.instance.use as any)(...args);
}
// init :313-325 — drain AFTER registerMiddie resolves, preserving order
if (this.pendingMiddlewares.length > 0) {
  for (const { args } of this.pendingMiddlewares) {
    (this.instance.use as any)(...args);
  }
  this.pendingMiddlewares = [];
}
```

**Flow:** Boot order is not guaranteed ⇒ every pre-init `use()` parks its exact argument tuple; `init()` awaits `registerMiddie()` FIRST then replays tuples in arrival order and clears the array. The route-middleware factory (`createMiddlewareFactory`) lazily awaits the same registration before producing `(path, callback)` installers. Inside an installer, `$`-suffixed paths get the anchor stripped and re-appended as a compiled regex suffix (`new RegExp(re.source + '$', re.flags)` :720-722), `/*path` falls back to bare `*path` for GraphQL-style plugins (:703-704), and root paths under a global prefix are rewritten to `<prefix>/{*path}` (:707-716) so prefix-scoped middleware still matches `/`.
**Invariant:** Middleware ORDER is the contract — FIFO replay preserves it; dropping or re-sorting queued tuples silently changes handler precedence. `use()` must return `this` in BOTH branches (queuing branch included) or chained boot wiring breaks. The `{ args }` wrapper exists so later mutation of caller arrays cannot corrupt the parked call.
**Probe:** Deterministic anchors (direct-test coverage caveat: spec covers reply/mapException only): `grep -n 'pendingMiddlewares' packages/platform-fastify/adapters/fastify-adapter.ts` = exactly 5 lines (:168 declaration, :320 drain guard, :321 replay loop, :324 queue clear, :769 push); `grep -n 'skipMiddie' packages/platform-fastify/adapters/fastify-adapter.ts` = 2 (:79 type member, :272 constructor check).
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"nest","query":"use queue middleware register later during init fastify adapter","limit":4}'
```
Live-verified @4c38a5ab1: rank#3 `FastifyAdapter.use packages/platform-fastify/adapters/fastify-adapter.ts 765-773`. Drift note: single-token query `pendingMiddlewares` returns total:0 (property token not in the BM25 index) and bare `middie` terms hit the vendored plugin internals — keep the multi-word adapter-plane phrasing.

## Verdict
Adopt the park-replay pattern for any async-required host capability (queue exact arg tuples, drain after capability ready, FIFO); adapt the `$`-anchor and `{*path}` prefix rewrite to your path grammar; omit find-my-way/middie internals.
