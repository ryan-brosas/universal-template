<!-- capsule-v2 -->
# Web tools — webfetch + websearch

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how do a web-fetch and web-search tools let the agent use the web safely?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/webfetch.ts` (192 lines): `Parameters`, `WebFetchTool`; `packages/opencode/src/tool/websearch.ts` (143 lines): `Parameters`, `WebSearchTool`.
**Signature:** `webfetch({url, ...})` fetches a URL's content; `websearch({query, ...})` runs a web search and returns results.
**Data Shape:** webfetch params `{url}`; websearch params `{query}`; both return text content/results.

### Decisive source
```ts
// webfetch.ts — fetch a URL and return its readable content
// websearch.ts — run a web search and return ranked results
```

**Flow:** the model calls `webfetch` with a URL (returns page content) or `websearch` with a query (returns results). Both are read-only, permission-gated like other tools, and let the agent ground on live web content.
**Invariant:** web access is permission-gated; results are bounded and returned as text.
**Probe:** `packages/opencode/test/tool/webfetch.test.ts` + `websearch.test.ts` (URL fetch returns content; search returns results; permission gate invoked).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "WebFetchTool WebSearchTool webfetch websearch url query", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the webfetch/websearch tool pair (permission-gated web access, text results); adapt the fetch/search backend to host.
