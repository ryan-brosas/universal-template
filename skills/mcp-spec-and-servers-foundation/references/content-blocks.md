<!-- capsule-v2 -->
# Content Blocks & Annotations — what may a tool result contain, and which annotations are hints vs trust anchors?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What are the exact content-block types a CallToolResult/PromptMessage can carry, where do display-annotations end and security-relevant hints begin, and how do unstructured and structured results coexist?

## The ContentBlock union
**Path/Symbol:** `schema/draft/schema.ts` (`ContentBlock` union :2305–2306, `Annotations` :2270–2300, `TextContent` :2316–2330, `ImageContent` :2340–2361, `AudioContent` :2371–2392, `ResourceLink` :1719–1732, `EmbeddedResource` :1734–1751, `CallToolResult` :1809–1838, `ToolUseContent` :2406–2431, `ToolResultContent` :2445+); prose `docs/specification/draft/server/tools.mdx` :402–505 (tool result content types), `docs/specification/draft/server/resources.mdx` :336–364 (annotations).

**Data Shape:** `ContentBlock = TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource` — the SAME union fills `CallToolResult.content[]`, every `PromptMessage.content`, and sampling messages. `CallToolResult = { content: ContentBlock[], structuredContent?: unknown, isError?: bool }`. Display annotations: `{ audience?: ("user"|"assistant")[], priority?: 0..1, lastModified?: ISO-8601 }`.

### Decisive source
```ts
// schema.ts:1900-1908 (the hint contract)
// Additional properties describing a Tool to clients.
// NOTE: all properties in `ToolAnnotations` are **hints**.
// They are not guaranteed to provide a faithful description of
// tool behavior (including descriptive properties like `title`).
// Clients should never make tool use decisions based on `ToolAnnotations`
// received from untrusted servers.

// tools.mdx:304-307 (normative MUST)
// For trust & safety and security, clients **MUST** consider tool
// annotations to be untrusted unless they come from trusted servers.

// schema.ts:1810-1821 (unstructured + structured coexist)
content: ContentBlock[];        // "unstructured result"
structuredContent?: unknown;    // JSON conforming to outputSchema if defined

// schema.ts:1824-1835 (isError semantics)
// Any errors that originate from the tool SHOULD be reported inside the
// result object, with `isError` set to true, _not_ as an MCP protocol-level
// error response. Otherwise, the LLM would not be able to see that an error
// occurred and self-correct.
```

**Flow:** server returns `CallToolResult` → client shows/forwards `content[]` per block's `audience` annotation (user-facing UI vs model context) and `priority` (context budgeting) → if the tool declared an `outputSchema`, `structuredContent` additionally carries the machine-readable result → on failure inside the tool, `isError: true` + explanatory text content (NOT a protocol error).

**The two annotation families (don't confuse them):**
1. **Display annotations** (`Annotations`: audience/priority/lastModified) — client-side rendering/context hints; no security meaning; shared by resources, templates, and all content blocks.
2. **Tool behavior hints** (`ToolAnnotations`: readOnlyHint/destructiveHint/idempotentHint/openWorldHint/title) — describe side-effect class for UX gating, but they are UNTRUSTED input from the server: clients MUST NOT gate real permissions on them from untrusted servers. Defaults: readOnly=false, destructive=true, idempotent=false, openWorld=true (conservative). `destructiveHint`/`idempotentHint` are meaningful only when `readOnlyHint == false`.

**Invariant:** one content union everywhere; text/image/audio are by-value, resource_link by-reference, embedded resource is ResourceContents inline; `isError` marks TOOL failures (LLM-visible), protocol errors mark REQUEST failures. A porter who treats `ToolAnnotations.readOnlyHint` as authorization, who drops structuredContent when emitting content blocks, or who reports tool errors as `-32xxx` protocol errors breaks the contract.

**Probe:** no runtime tests in the spec repo; wire types + `scripts/validate-examples.ts` are machine-checkable anchors (`examples/CallToolResult*`, `examples/ImageContent/*`). Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "ContentBlock|TextContent|AudioContent|CallToolResult", limit: 10 });
```

## Verdict
Adopt the five-type ContentBlock union as the single result/message currency, dual unstructured+structured emission, isError-for-tool-failures, and display-vs-behavior annotation split with the untrusted-hints rule; adapt your rendering and permission UX to host; omit making any access-control decision from ToolAnnotations (hard rule).
