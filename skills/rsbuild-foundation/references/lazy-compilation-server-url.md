<!-- capsule-v2 -->
# lazyCompilation serverUrl derivation — why does a relative assetPrefix mean "follow page origin" and single-entry skip entries?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce when the lazy backend URL is absolute vs omitted, and the entries/imports toggles.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/lazyCompilation.ts` — `getServerUrlFromClientConfig` 6–38, plugin 40–109 (single-entry branch 62–75, placeholder rewrite 88–98).
**Signature:** `getServerUrlFromClientConfig(config, context): Promise<string | undefined>`.
**Data Shape:** dev.lazyCompilation: true | {entries?, imports?, serverUrl?}; apply:'serve' (plugin only registered for dev).

### Decisive source
```ts
// A relative asset prefix indicates that page requests are routed through the
// current origin, so the lazy compilation endpoint should follow the same route.
const hasAbsoluteAssetPrefix = assetPrefix === true || (typeof assetPrefix === 'string' && isURL(assetPrefix));
if (!hasAbsoluteAssetPrefix) return;                       // undefined → bundler default (same-origin)
if (!hasClientHost && !hasClientPort) return;
const protocol = client.protocol ? `${client.protocol === 'wss' ? 'https' : 'http'}:` : '';
const port = client.port && client.port !== '<port>' ? client.port : devServer.port;
return `${protocol}//${hostname}:${port}`;
```
```ts
// If there is only one entry, do not enable lazy compilation for entries — this can reduce the rebuild time
if (Object.keys(entries).length <= 1) chain.lazyCompilation({ entries: false, imports: true, ...(serverUrl ? { serverUrl } : {}) });
```

**Flow:** object-form serverUrl gets `<port>` replaced from the live devServer before handoff. Lazy compilation additionally requires hmr||liveReload (dev client must fetch compiled modules) and web target only. infrastructureLog mining of which modules got lazily requested feeds createCompiler's build log (see compiler-lifecycle capsule).
**Invariant:** (1) forcing an absolute serverUrl while the app is served same-origin breaks the lazy endpoint behind proxies — omit instead; (2) wss→https mapping must pair or mixed-content kills the trigger requests; (3) multi-entry apps need entries:true or secondary pages never compile on demand.
**Probe:** e2e `cases/lazy-compilation/basic/index.test.ts:6/:34`, `client-url/index.test.ts:26/:89` (client host/port + relative-assetPrefix origin-follow).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginLazyCompilation getServerUrlFromClientConfig replacePortPlaceholder", limit: 8 });
```

## Verdict
Adopt origin-following default with explicit-URL override and single-entry optimization. Adapt protocol pairing to host TLS scheme. Omit rspack lazyBackend internals.
