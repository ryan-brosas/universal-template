<!-- capsule-v2 -->
# System-proxy merge ladder — environment variables beat OS settings, and detection must be single-flight

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** When a client auto-detects proxy config, how do env vars, OS-level settings, and PAC URLs combine — and how do you avoid spawning three concurrent OS probes?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/network/system-proxy/index.ts:SystemProxyResolver` (:8-84) + `getSystemProxy` (:86-105); helpers in `network/system-proxy/utils/common.ts` (`normalizeProxyUrl` :36, `normalizeNoProxy` :53, `safeExec` :15).
**Signature:** `getSystemProxy() → Promise<ProxyConfiguration>` where `ProxyConfiguration = {http_proxy, https_proxy, no_proxy, pac_url?, source}`.
**Data Shape:** per-resolver `activeDetection: Promise | null` single-flight latch; platform detectors (windows/macos/linux) invoked with `{timeoutMs: 10000 default}`; env read is synchronous and always available.

### Decisive source
```ts
try {
  const systemProxyEnvironmentVariables = await systemProxyResolver.getSystemProxy();
  return {
    http_proxy: proxyEnvironmentVariables?.http_proxy || systemProxyEnvironmentVariables?.http_proxy,
    https_proxy: proxyEnvironmentVariables?.https_proxy || systemProxyEnvironmentVariables?.https_proxy,
    no_proxy: proxyEnvironmentVariables?.no_proxy || systemProxyEnvironmentVariables?.no_proxy,
    pac_url: systemProxyEnvironmentVariables?.pac_url || null,
    source: hasEnvironmentProxy ? `${systemProxyEnvironmentVariables?.source} + environment` : systemProxyEnvironmentVariables?.source
  };
} catch (error) {
  return proxyEnvironmentVariables; // OS probe failed → env-only answer, never throw
}
```

**Flow:** read env first (lowercase beats uppercase beats ALL_PROXY/ALL_PROXY per slot; `no_proxy` normalized `[;,\s]+ → comma`) → if any env proxy exists still run the OS detector but ENV WINS every slot via `||` precedence → OS failure degrades to env-only result with `pac_url: null` → slow detections (>5s) console.warn. Single-flight: `getSystemProxy()` returns the in-flight promise if present, clears the latch in `finally`.
**Invariant:** `normalizeProxyUrl` prepends `http://` ONLY when no `^[a-z][a-z0-9+.-]*://` scheme is present (system proxies omit schemes; assuming https breaks them); OS-probe failure is data-loss-not-crash (return env); the `source` string concatenation records BOTH origins so debug UIs can show provenance. Platform dispatch throws on unsupported platforms rather than guessing.
**Probe:** `packages/bruno-requests/src/network/system-proxy/index.spec.js` :1-278 — pins lowercase-over-uppercase priority, uppercase fallback, ALL_PROXY fill, no_proxy normalization, and per-platform delegation (jest-swapped `process.env` plain object keeps case-distinct keys working on Windows' case-insensitive real env — itself a porting lesson).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "SystemProxyResolver detectByPlatform", limit: 5 });
// resolves detectByPlatform :55-66 + getSystemProxy :20-35
```

## Verdict
Adopt env-beats-OS `||` merge, single-flight detection, fail-open-to-env error handling, and scheme-normalization guard. Adapt per-platform detectors to your OS APIs; omit Bruno's warn threshold. Coverage caveat: none — clean coverage at pin.
