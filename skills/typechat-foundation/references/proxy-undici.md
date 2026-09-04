<!-- capsule-v2 -->
# Proxy support — how is optional undici egress wired without a hard dependency?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How do I route model traffic through HTTP(S)_PROXY/ALL_PROXY/NO_PROXY or an explicit URL, loading undici lazily and failing with an actionable message?

## ProxySettings + lazy dispatcher
**Path/Symbol:** `typescript/src/model.ts:128-138` (`ProxySettings` union + `InternalModelOptions`), `:529-537` (`proxySettingsFromEnv`), `:543-552` (`resolveProxySettings`), `:559-571` (`importUndici`), `:578-596` (`resolveProxyDispatcher`); consumed via `dispatcherPromise ??= resolveProxyDispatcher(proxy)` at :248/:341.
**Signature:** `type ProxySettings = { kind:"url"; url:string } | { kind:"env"; httpProxy?; httpsProxy?; noProxy? }`; `resolveProxyDispatcher(proxy): Promise<RequestInit["dispatcher"] | undefined>`.
**Data Shape:** env collection order: HTTPS_PROXY ?? https_proxy ?? ALL_PROXY ?? all_proxy (https), mirror for http; NO_PROXY passed through. Both upper- AND lower-case recognized.

### Decisive source
```ts
if (proxy.kind === "url") {
    return new ProxyAgent(proxy.url) as unknown as RequestInit["dispatcher"];
}
const envOptions = {
    ...(proxy.httpProxy ? { httpProxy: proxy.httpProxy } : {}),
    ...(proxy.httpsProxy ? { httpsProxy: proxy.httpsProxy } : {}),
    ...(proxy.noProxy ? { noProxy: proxy.noProxy } : {})
};
return new EnvHttpProxyAgent(envOptions) as unknown as RequestInit["dispatcher"];
```
**Flow:** factory resolves settings once → per-complete, dispatcher promise memoized (`??=`) so undici imports at most once per model instance → dispatcher attached to RequestInit only if truthy.
**Invariant:** undici is OPTIONAL — `importUndici()` translates ERR_MODULE_NOT_FOUND into "A proxy was configured, but the optional \"undici\" package is not installed. Run \"npm install undici\"..." instead of an opaque crash. Absent proxy settings return undefined BEFORE any import (an agent is never constructed from empty strings). The double cast exists because undici's dispatcher types are nominally distinct from Node's `undici-types` copy — structurally identical, bridged by `as unknown as`.
**Probe:** `grep -c 'EnvHttpProxyAgent' typescript/src/model.ts` (=5 occurrences across type/comment/code); `grep -c 'proxySettingsFromEnv(env)' typescript/src/model.ts` (=1 call site inside createLanguageModel :158). No direct test at this pin (tests mock fetch without dispatchers) — coverage caveat recorded honestly.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"proxy undici dispatcher ProxyAgent","limit":4}'
```

## Verdict
Adopt the lazy-import + actionable-error pattern for any optional heavy dep; adapt agent choice if the host runtime already exposes dispatcher support; omit entirely for non-Node runtimes. Coverage caveat: no direct test exercises the dispatcher path — verify against live proxy when porting.
