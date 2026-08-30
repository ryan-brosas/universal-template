<!-- capsule-v2 -->
# Base-URL path-append delegation — how much of the endpoint URL does the extension own, and how much does the host's API client own?

**Source:** pi-bailian MIT `main@c26c4e9855c87b18b17d5717b8c9171a27031d06`; Codebase Memory `pi-bailian`. **Question:** Where does the version path (`/v1/messages`) get added when the provider speaks an Anthropic-compatible protocol?

## Base-URL ownership seam
**Path/Symbol:** `src/index.ts` `BAILIAN_INTL_BASE_URL` (:14-18), `BAILIAN_CN_BASE_URL` (:20-24); corroborated by README :163-171.
**Signature:** `const BAILIAN_INTL_BASE_URL = "https://coding-intl.dashscope.aliyuncs.com/apps/anthropic";`
**Data Shape:** registered `baseUrl` ends at the vendor's app-scoped prefix; NO version path, NO trailing resource.

### Decisive source
```ts
/**
 * International (global) endpoint for Bailian Coding Plan
 * Pi's anthropic-messages API appends /v1/messages automatically
 */
const BAILIAN_INTL_BASE_URL = "https://coding-intl.dashscope.aliyuncs.com/apps/anthropic";
```

**Flow:** extension registers `api: "anthropic-messages"` + prefix-only `baseUrl` → host's anthropic-messages implementation constructs `<baseUrl>/v1/messages` per request → final URL `…/apps/anthropic/v1/messages`.
**Invariant:** the extension must NOT include `/v1/messages` in `baseUrl` — doing so double-appends and breaks every request. The doc comment above each constant is the contract carrier; the choice of `api` adapter determines which path segment gets appended.
**Probe:** no upstream unit test exercises URL assembly (the constants are consumed only by `registerProvider`; README :168-170 documents the assembled final URL). Recorded coverage caveat: this capsule rests on source + docs reads, not a direct test. Runner BLOCKED this pass (no node_modules).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-bailian", query: "anthropic messages endpoint base URL dashscope", limit: 6, fields: ["signature", "lines"] });
```
Executed live at pin: total **0** — BM25 has no Function/Variable node carrying the URL vocabulary at this pin (constants live inside module scope of the unnamed default-export file). The seam is addressed by direct read of `src/index.ts:14-24`; recorded as an honest retrieval gap, not papered over.

## Verdict
Adopt prefix-only baseUrl with the append responsibility delegated to the host adapter, documented inline at each constant. Adapt the prefix to your gateway's real app-scoped root. Omit any client-side URL joining in the extension — that is the bug class this seam exists to prevent.
