<!-- capsule-v2 -->
# MCP App server-side resource contract — how does @ai-sdk/mcp normalize app resources, metadata, and visibility?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does the MCP client package turn raw `tools/list` + `resources/read` payloads into typed, render-ready MCP App data without failing on malformed servers?

## Lenient-parse metadata, strict-throw resource reads
**Path/Symbol:** `packages/mcp/src/tool/mcp-apps.ts` — `getMCPAppToolMeta` (:140–163), `MCP_APP_LEGACY_RESOURCE_URI_META_KEY='ui/resourceUri'` (:27), `optionalStringArray` `.catch(undefined)` schema (:95–99), `splitMCPAppTools` (:182–212), `getMCPAppResourceFromReadResult` (:230–263), `readMCPAppResource` (:268–285), extension capability (:16–38).
**Signature:** `readMCPAppResource({client, uri, options?}): Promise<MCPAppResource>`; `splitMCPAppTools(definitions) → {modelVisible, appVisible}`.
**Data Shape:** `MCPAppResource = {uri, mimeType: 'text/html;profile=mcp-app', html, meta?: {prefersBorder?, csp?, permissions?}}`.

### Decisive source
```ts
const resourceUri =
  uiMeta?.resourceUri ?? tool._meta?.[MCP_APP_LEGACY_RESOURCE_URI_META_KEY];
if (resourceUri !== undefined) {
  if (typeof resourceUri !== 'string' || !resourceUri.startsWith('ui://'))
    throw new Error(`Invalid MCP App resource URI: ...`);   // STRICT here
}
...
const content = resource.contents.find(content => content.uri === uri);
if (content == null) throw new Error(`MCP App resource not found in read result: ${uri}`);
if (content.mimeType !== MCP_APP_MIME_TYPE)
  throw new Error(`Unsupported MCP App resource MIME type: ${content.mimeType}`);
const html = 'text' in content && typeof content.text === 'string'
  ? content.text
  : 'blob' in content && typeof content.blob === 'string'
    ? new TextDecoder().decode(convertBase64ToUint8Array(content.blob))
    : undefined;                                            // then throw
```

**Flow:** tool definitions flow through `getMCPAppToolMeta`, which prefers `_meta.ui.resourceUri` and falls back to the DEPRECATED flat `ui/resourceUri` key for older servers → a present-but-invalid URI THROWS (host misconfiguration must be loud), while malformed optional fields (visibility arrays, `_meta.ui` shapes) are silently FILTERED via `.catch(undefined)`/element-filtering schemas so one bad server field can't break the whole tool list → `splitMCPAppTools` routes tools by visibility with null meaning model-visible → resource reads locate the exact uri in `contents[]`, enforce the MIME type, decode text or base64-blob HTML, and lenient-parse `_meta.ui` rendering metadata.
**Invariant:** Two different failure philosophies at two layers: IDENTITY fields throw, EMBELLISHMENT fields degrade. A port that lenient-parses the URI lets tools silently lose their apps; a port that throws on malformed `csp` lets one sloppy server break every list call. Visibility default is asymmetric BY DESIGN: absent = model-visible only; `'app'` inclusion is always explicit.
**Probe:** deterministic: `grep -n "ui/resourceUri" packages/mcp/src/tool/mcp-apps.ts` → `27:`; `grep -n "visibility.includes('model')" packages/mcp/src/tool/mcp-apps.ts` → `193:`; `grep -n "convertBase64ToUint8Array(content.blob)" packages/mcp/src/tool/mcp-apps.ts` → `253:`; `grep -n "io.modelcontextprotocol/ui" packages/mcp/src/tool/mcp-apps.ts` → `16:`. Direct tests: `mcp-apps.test.ts:82` legacy key, `:90` invalid-URI throw, `:98` visibility split, `:134/:166` text/blob reads, `:192` malformed-meta drop.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "splitMCPAppTools visibility", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 mcp-apps.splitMCPAppTools :182-212
```

## Verdict
Adopt the identity-throws/embellishment-degrades split and the dual-key legacy fallback; adapt the MIME constant and capability extension name to your spec revision; omit nothing — collapsing either failure class into the other produces silent app loss or fleet-wide breakage.
