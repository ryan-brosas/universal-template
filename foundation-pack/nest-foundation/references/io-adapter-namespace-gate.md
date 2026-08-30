<!-- capsule-v2 -->
# io-adapter namespace gate — when does create() return the Server versus a Namespace, and why does `server.of` need a namespace to fire?

**Source:** nest MIT `master@4c38a5ab1` (drift commit window: return type widened + `namespace &&` added); Codebase Memory project `nest`. **Question:** Given user-supplied `{ namespace?, server? }` options, which object must `create()` hand back and under what exact conditions?

## Server | Namespace decision ladder over {namespace, server}
**Path/Symbol:** `packages/platform-socket.io/adapters/io-adapter.ts:17-30 IoAdapter.create`; port-0 reuse in `createIOServer :32-37`.
**Signature:** `create(port: number, options?: ServerOptions & { namespace?: string; server?: Server }): Server | Namespace`.
**Data Shape:** Return widened from `Server` to `Server | Namespace` (this drift window); `options.server` narrowed from `any` to `Server`. `namespace` absent ⇒ plain Server. `disconnectMap: WeakMap<Socket, Observable<any>>` (:15) caches per-socket disconnect streams.

### Decisive source
```ts
// io-adapter.ts:25-29
return server && namespace && isFunction(server.of)
  ? server.of(namespace)
  : namespace
    ? this.createIOServer(port, opt).of(namespace)
    : this.createIOServer(port, opt);
```

**Flow:** No options ⇒ bare `createIOServer(port)`. Options present: (1) BOTH a server AND a namespace AND that server actually exposes `.of` ⇒ attach namespace onto the USER's server (`server.of(namespace)`); (2) namespace only ⇒ create a fresh server then `.of(namespace)` on it; (3) server without namespace ⇒ user's server as-is (the `&& namespace` addition makes an explicitly-provided server WITHOUT a namespace return that server directly instead of falling through toward `.of`). Port 0 with a shared httpServer ⇒ `new Server(this.httpServer, options)` — reuses the HTTP listener instead of binding a new port.
**Invariant:** `server.of` is only ever invoked when a namespace was requested — attaching a namespace to a provided server without one would silently change its routing surface. The `isFunction(server.of)` guard keeps duck-typed/mocked servers safe. Namespace attachment ALWAYS terminates the ladder; you never get both a new Server AND the user's Server for one call.
**Probe:** Direct test `packages/platform-socket.io/test/io-adapter.spec.ts:12-46` ("should register only one disconnect listener regardless of call count") pins the WeakMap single-subscription contract: two `bindMessageHandlers` calls on one socket ⇒ exactly ONE 'disconnect' listener registered but TWO 'test-event' listeners (per-call handler registration). Deterministic anchors: `grep -c "namespace &&" packages/platform-socket.io/adapters/io-adapter.ts` = 1 at :25; `grep -n "Server | Namespace" packages/platform-socket.io/adapters/io-adapter.ts` = 1 at :20.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"nest","query":"IoAdapter create namespace server of socket.io","limit":5}'
```

## Verdict
Adopt the three-arm ladder + WeakMap disconnect dedupe (shared-socket gateways register once); adapt the port-0 httpServer reuse to your server lifecycle; omit socket.io typing details. Coverage caveat: only bindMessageHandlers has a direct test — the create() ladder is source-pinned.
