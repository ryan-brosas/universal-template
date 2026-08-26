<!-- capsule-v2 -->
# publicPath resolution ladder — why does dev default to a <port> placeholder and 0.0.0.0 rewrite to localhost?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce prod/dev assetPrefix selection, the placeholder substitution timing, and ESM/server library-type coupling.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/output.ts` — `getPublicPath` 8–49, js/chunk filenames 76–100 (async path rule 51–60), const:false for web 102–109, server library type 113–118, ESM switch 120–135, copy plugin 137–142.
**Signature:** `getPublicPath({isDev, config, context}): string`.
**Data Shape:** `dev.assetPrefix: true | string`; `output.assetPrefix: string`; `<port>` placeholder resolved via replacePortPlaceholder.

### Decisive source
```ts
if (!isDev) { if (typeof output.assetPrefix === 'string') publicPath = output.assetPrefix; }
else if (typeof dev.assetPrefix === 'string') publicPath = dev.assetPrefix;
else if (dev.assetPrefix) {                       // true → derive from live dev server
  const protocol = context.devServer?.https ? 'https' : 'http';
  const hostname = context.devServer?.hostname || LOCALHOST;
  // http://0.0.0.0:port can't be visited on Windows:
  publicPath = hostname === ALL_INTERFACES_IPV4 ? `${protocol}://localhost:<port>/` : `${protocol}://${hostname}:<port>/`;
  if (server.base && server.base !== '/') publicPath = urlJoin(publicPath, server.base);
}
const port = isDev ? (context.devServer?.port ?? defaultPort) : defaultPort;
return formatPublicPath(replacePortPlaceholder(publicPath, port));
```
```ts
if (target === 'web' || target === 'web-worker') chain.output.merge({ environment: { const: false } }); // TDZ checks in browsers
```

**Flow:** prod uses output.assetPrefix verbatim; dev with true synthesizes from the RUNNING server context (which is why the value differs per boot); dev with explicit string wins over synthesis. Async chunks land under `js/async/` unless overridden or server target (where async===sync dir). output.module flips chunkFormat/chunkLoading to module/import and forbids web-worker targets loudly.
**Invariant:** (1) placeholder replacement must happen AFTER server.base joining or base URLs containing ports break; (2) `const:false` exists because Rspack's const-injected runtime hits browser TDZ — removing it breaks Safari/older Chrome only at runtime; (3) server builds always get commonjs2/module library type or SSR require() returns nothing.
**Probe:** unit `packages/core/tests/output.test.ts` (14 cases incl. filename/publicPath tables); e2e `cases/server/base-url-env-var`, `asset-prefix` cases.

## Get surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginOutput getPublicPath replacePortPlaceholder getJsAsyncPath", limit: 8 });
```

## Verdict
Adopt the three-way prefix ladder with late port substitution and localhost rewriting for bind-all hosts. Adapt defaults (port, dist dirs) to host. Omit copy-plugin wiring (thin rspack passthrough).
