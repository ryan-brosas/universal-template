<!-- capsule-v2 -->
# MCP App tool-part extraction — how is app metadata read from a UI tool part, and when is the app kept alive?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** What shape must `toolMetadata.app` have to render an MCP App, and how does the renderer survive streaming part churn?

## Strict metadata gate + last-good-app cache
**Path/Symbol:** `packages/react/src/mcp-apps/utils.ts` — `getMCPAppFromToolPart` (:25–46), `normalizeMCPAppToolResult` (:62–79); `packages/react/src/mcp-apps/app-renderer.tsx` — `cachedApp` functional update (:37–43), stale-resource guard (:75–78), load effect with cancellation (:47–73).
**Signature:** `getMCPAppFromToolPart(part): MCPAppMetadata | undefined`; `normalizeMCPAppToolResult(output): { content, structuredContent?, isError? }`.
**Data Shape:** valid app metadata = JSON object with `mimeType === 'text/html;profile=mcp-app'`, string `resourceUri` starting `ui://`, optional `visibility` array whose members are all `'model'|'app'`.

### Decisive source
```ts
if (appMetadata == null ||
    appMetadata.mimeType !== 'text/html;profile=mcp-app' ||   // exact MIME
    typeof appMetadata.resourceUri !== 'string' ||
    !appMetadata.resourceUri.startsWith('ui://') ||
    (appMetadata.visibility != null &&
      (!Array.isArray(appMetadata.visibility) ||
        appMetadata.visibility.some(v => v !== 'model' && v !== 'app'))))
  return undefined;                       // ANY deviation ⇒ not an app
```
```tsx
setCachedApp(previous =>
  previous?.resourceUri === app.resourceUri ? previous : app); // hold identity
...
const loadedResourceForApp =
  loadedResource?.resourceUri === appForRender?.resourceUri   // stale-drop
    ? loadedResource : undefined;
```

**Flow:** renderer extracts metadata from `part.toolMetadata?.app` → invalid ⇒ fallback node → valid: while a part streams, its object identity changes every chunk, so the renderer pins the FIRST metadata per `resourceUri` (functional updater returning `previous`) and only swaps on a URI change → resource loads via prop or `loadResource` callback with `cancelled` cleanup flag → late-arriving resources for a superseded URI are discarded by the stale-guard → output normalization wraps structured-only results as `{content:[], structuredContent}` so the iframe always receives MCP-shaped results.
**Invariant:** The exact-MIME check (`;profile=mcp-app` suffix included) plus ui:// prefix make app rendering opt-in per tool — plain HTML tools never become iframes. Identity-stability is behavioral, not cosmetic: re-rendering the iframe per streamed chunk would tear down and re-handshake the app on every token.
**Probe:** deterministic: `grep -n "appMetadata.mimeType !== 'text/html;profile=mcp-app'" packages/react/src/mcp-apps/utils.ts` → `33:`; `grep -n "structuredContent: output" packages/react/src/mcp-apps/utils.ts` → `77:`; `grep -n "previous?.resourceUri === app.resourceUri ? previous : app" packages/react/src/mcp-apps/app-renderer.tsx` → `40:`; `grep -n "loadedResource?.resourceUri === appForRender?.resourceUri" packages/react/src/mcp-apps/app-renderer.tsx` → `76:`. Direct tests: `utils.test.ts:6/:35`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "getMCPAppFromToolPart normalize", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: resolves utils.ts symbols (BM25 rank#1 family)
```

## Verdict
Adopt the strict metadata gate, URI-keyed identity pinning, and stale-resource drop; adapt the metadata location (`toolMetadata.app`) to your part schema; omit nothing — identity-churn re-mounts are the wrong port this capsule prevents.
