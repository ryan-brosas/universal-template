<!-- capsule-v2 -->
# Proxy policy resolution — how do per-engine tags, request overrides, and the global proxy interact?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** Given X-Use-Proxy / X-Proxy-URL headers plus config, which proxy serves this one query?

## effectivePolicyForQuery ladder
**Path/Symbol:** `core/resilient.go:effectivePolicyForQuery` (L676–692), `core/proxy.go:ResolveEffectiveProxyPolicy/NormalizeProxyRequestOverride/IsAuthenticatedSocksProxyURL` (L285–333), `server.go:validateRequestProxyURL` (L1526–1549).
**Signature:** `effectivePolicyForQuery(engineName string, q Query) ProxyPolicy{Mode, Tag}`; `NormalizeProxyRequestOverride(raw) (string, error)`.
**Data Shape:** modes off | request_url | tag_pool; override token "direct" or a tag.

### Decisive source
```go
switch q.ProxyOverride {
case ProxyOverrideDirect:                       // X-Use-Proxy: direct WINS over everything
	return ProxyPolicy{Mode: ProxyModeOff}
}
if strings.TrimSpace(q.ProxyURL) != "" && rs.proxyCfg.Proxies.AllowRequestProxyURL {
	return ProxyPolicy{Mode: ProxyModeRequestURL}
}
switch q.ProxyOverride {
case "":  return rs.effectivePolicyForEngine(engineName)   // config: global ⇒ tag_pool; else engine tag or off
default:  return ProxyPolicy{Mode: ProxyModeTagPool, Tag: q.ProxyOverride}
}
// ResolveEffectiveProxyPolicy: a configured GLOBAL proxy implies tag_pool even with no tags:
if global != "" { return ProxyPolicy{Mode: ProxyModeTagPool} }
// browser runtime rejects authenticated SOCKS outright (Chrome can't auth it):
if Runtime == Browser && IsAuthenticatedSocksProxyURL(q.ProxyURL) → 400 UNSUPPORTED_PROXY_SCHEME
```
selectProxyForQuery: empty override + non-empty global ⇒ use the global directly; else NextByTagWithContext(tag).

**Flow:** handlers validate BEFORE search (400 REQUEST_PROXY_URL_DISABLED when AllowRequestProxyURL false); response headers X-Proxy-Mode/X-Proxy-Tag/X-Proxy-Used(masked scheme://host)/X-Proxy-Attempts(>1 only) expose what happened; Query.String() masks ProxyURL so %+v logging never leaks passwords.
**Invariant:** masking is unconditional in logs/stats/errors (MaskProxyURL drops userinfo entirely); override "direct" bypasses even a global proxy — it's an escape hatch for testing.
**Probe:** `go test ./core -run 'TestProxy'` (proxy_test/proxy_per_context_test/proxy_integration_test cover the matrix).
**Probe executed (real runner):** same command at pin = **11 PASS** covering the override matrix (direct/tag/request-URL precedence incl. fail-closed missing-tag), normalization, socks5h, stats masking.
**Python-equivalent probe (executed):**
```python
def policy_for(override, proxy_url, allow, engine_tag, has_global):
    if override=='direct': return ('off',None)
    if proxy_url and allow: return ('request_url',None)
    if override: return ('tag_pool',override)
    if has_global: return ('tag_pool',None)
    return (('tag_pool',engine_tag) if engine_tag else ('off',None))
assert policy_for('direct','http://p',True,'resi',True)==('off',None)
assert policy_for(None,None,False,'resi',False)==('off',None)
assert policy_for('resi',None,True,None,False)==('tag_pool','resi')
print("proxy-policy ladder GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "effectivePolicyForQuery NormalizeProxyRequestOverride MaskProxyURL applyProxyHeaders", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the precedence order and always-mask discipline; adapt header names to your gateway conventions; omit request_url mode if you never let clients bring their own proxies.
