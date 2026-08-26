<!-- capsule-v2 -->
# Network-proxy identity guard — how do you patch fetch/XHR/sendBeacon without ever stacking a proxy on a proxy?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** When an iframe or SPA re-runs network instrumentation on an already-patched context, what prevents double interception and double-sent messages?

## Symbol-keyed original slot + unwrap-before-wrap
**Path/Symbol:** `networkProxy/src/index.ts:isProxied` (:20-21), `unwrap` (:22-23), `wrap` (:24-27), `createNetworkProxy` (:53-117); re-patch driver `tracker/tracker/src/main/modules/network.ts:patchWindow` (:134-165) + `attachContextCallback` (:366-368).
**Signature:** `wrap<T extends Function>(proxy: T, orig: Function): T`; `unwrap<T extends Function>(fn: T): T`; `createNetworkProxy(context, ignoredHeaders, setSessionTokenHeader, sanitize, sendMessage, isServiceUrl, modules?, tokenUrlMatcher?): void`.
**Data Shape:** `OR_FLAG = Symbol('OpenReplayProxyOriginal')` lives per module instance; each patched global carries exactly one hidden original. Iframes re-enter via the observer's context callback with their own `globalThis`.

### Decisive source
```ts
const OR_FLAG   = Symbol('OpenReplayProxyOriginal')
const isProxied = (fn: any): fn is Function & { [OR_FLAG]: Function } =>
  !!fn && fn[OR_FLAG] !== undefined
const unwrap    = <T extends Function>(fn: T) =>
  isProxied(fn) ? (fn as any)[OR_FLAG] as T : fn

// createNetworkProxy, per API:
const original = unwrap(context.XMLHttpRequest)
if (!original) warn('XMLHttpRequest')
else context.XMLHttpRequest = wrap(XHRProxy.create(...), original)
```

**Flow:** patch request → `unwrap()` collapses any existing chain back to the browser original → build new proxy → `wrap()` stores that original under the symbol → assign to context. Iframes call the same function later; the symbol guarantees the second pass replaces rather than nests.
**Invariant:** A patched API must always be exactly one proxy deep. Nesting would make every app request produce N recorded messages and let token headers be appended N times. The original must stay reachable for teardown/migration.
**Probe:** `grep -c 'OR_FLAG' networkProxy/src/index.ts` → `5`; `grep -c 'unwrap(context' networkProxy/src/index.ts` → `3` (xhr, fetch, beacon each unwrap first).
**Coverage:** index.ts + network.ts `no_recorded_issue`/`metadata_match` @ gen 2026-08-25T20:08:30Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "isProxied unwrap wrap createNetworkProxy proxy original context", limit: 10 });
```
(Executed at pin: top 4 hits were createNetworkProxy/unwrap/isProxied/wrap in networkProxy/src/index.ts.)

## Verdict
Adopt symbol-keyed originals + unwrap-before-wrap for any global monkey-patching. Adapt the flag name/storage to your teardown story. Omit the console.warn fallback if you fail loud instead.
