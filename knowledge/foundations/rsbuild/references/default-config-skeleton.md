<!-- capsule-v2 -->
# defaultConfig normalization skeleton — why are defaults FACTORY functions and assetPrefix a deferred placeholder?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce which defaults exist, their cross-key couplings (base→assetPrefix, polyfill→entry), and the shared-origin CORS regex.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/defaultConfig.ts` — dev 44–63 (client.path=HMR_SOCKET_PATH, reconnect:100, browserLogs.stackTrace), `defaultAllowedOrigins` 81–82, server 84–97 (htmlFallback:'index', cors origin regex), source 101–109 (decorators '2023-11'), html 111–120+ (meta charset+viewport, inject:'head'), plus output/perf/tools sections to 377.
**Signature:** per-section factory fns (`getDefaultDevConfig()` etc.) invoked during normalization.
**Data Shape:** Normalized* types = fully-materialized records; every list-valued key is an ARRAY post-normalization.

### Decisive source
```ts
export const defaultAllowedOrigins: RegExp =
  /^https?:\\/\\/(?:(?:[^:]+\\.)?localhost|127\\.0\\.0\\.1|\\[::1\\])(?::\\d+)?$/;
// any-subdomain localhost + loopback v4/v6 with optional port — the ONLY origins CORS opens by default
```
```ts
client: { path: HMR_SOCKET_PATH, port: '', host: '', overlay: true, reconnect: 100, logLevel: 'info' },
...
source: { define:{}, preEntry:[], decorators:{ version:'2023-11' } },   // modern decorators BY DEFAULT
```

**Flow:** factories (not literals) so each environment normalization gets fresh objects — two environments sharing a default array would mutate each other. dev.assetPrefix placeholder ('<port>'-bearing or true) is resolved LATER by pluginOutput against the live server context. htmlFallback 'index' drives middleware-stack slot insertion (see pass-1 capsules).
**Invariant:** (1) NEVER hoist default objects to module scope — normalized configs are mutated in place per env; (2) defaultAllowedOrigins intentionally includes subdomains of localhost (*.localhost resolves to loopback on most stacks) but NOT 0.0.0.0; (3) decorators default flipped legacy→'2023-11' — porters copying older rsbuild versions inherit the wrong transform.
**Probe:** snapshot suites `packages/core/tests/default.test.ts` + config.test.ts pin the full materialized object.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "defaultAllowedOrigins getDefaultDevConfig getDefaultServerConfig", limit: 8 });
```

## Verdict
Adopt factory-per-env defaults, the loopback-only CORS regex, and decorator/modern-default posture. Adapt concrete values (ports, paths) to host. Omit documentation comments.
