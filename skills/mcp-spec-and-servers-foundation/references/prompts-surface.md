<!-- capsule-v2 -->
# Prompts Surface — how do prompts/get messages work, and what may a prompt message contain?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What is the exact contract for exposing prompt templates — user-controlled selection, argument customization, and the five content types a PromptMessage may embed?

## Listing and getting
**Path/Symbol:** `docs/specification/draft/server/prompts.mdx` (whole; capability :39–64; prompts/list :66–120; prompts/get :122–165; list-changed :167–179; data types :206–317; error handling :319–325); wire types `schema/draft/schema.ts` (`ListPromptsRequest` :1566–1576, `GetPromptRequestParams` :1602–1619, `GetPromptResult` :1634–1648, `Prompt` :1659–1676, `PromptArgument` :1678–1692, `Role` :1694, `PromptMessage` :1704–1717, `ResourceLink` :1719–1732, `EmbeddedResource` :1734–1751).

**Data Shape:** capability `prompts: { listChanged?: bool }`. `Prompt` = `{ name, title?, description?, arguments?: [{ name, description?, required? }], icons? }`. `prompts/get` takes `{ name, arguments? }` → `{ description?, messages: PromptMessage[] }`. `PromptMessage` = `{ role: "user"|"assistant", content: ContentBlock }`.

**Interaction model (who decides):** prompts are **user-controlled** (typically slash commands) — the USER decides when one runs; resources are **application-driven** (the HOST app decides what context to include); tools are **model-controlled** (the LLM decides). Content authorship is always the server's.

### Decisive source
```md
# prompts.mdx:57-64 (same stability invariant as resources)
Servers that declare the `prompts` capability MUST respond to `prompts/list`
requests with the set of prompts currently available. This set MAY be empty
and MAY change over time, but MUST NOT vary per-connection or as a side
effect of other requests on the connection. The set MAY vary by the
authorization presented on the request — since credentials are per-request
input, not connection state.

# prompts.mdx:323-324 (error mapping)
Invalid prompt name: -32602 (Invalid params)
Missing required arguments: -32602 (Invalid params)
```

**Flow:** `prompts/list` (+cursor/ttlMs/cacheScope) → user picks one → `prompts/get {name, arguments}` → server returns rendered `messages[]` the client injects into the conversation → list changes ride `notifications/prompts/list_changed`, but ONLY to clients holding an open `subscriptions/listen` stream with `promptsListChanged: true`.

**MRTR applies:** `prompts/get` MAY answer `InputRequiredResult` (gather missing inputs); client retries with `inputResponses` + NEW id.

**The five content types of a prompt message:**
1. `text` — `{ type:"text", text }`.
2. `image` — base64 `data` + `mimeType` (MUST).
3. `audio` — base64 `data` + `mimeType` (MUST).
4. `resource_link` — link WITHOUT contents (`{ type:"resource_link", uri, name, ... }`) — client fetches later; carries resource annotations.
5. `resource` (embedded) — contents INLINE (`{ type:"resource", resource: ResourceContents }`) — server-managed material injected directly into the conversation.

All content types support optional annotations (`audience`/`priority`/`lastModified`).

**Invariant:** same connection-stable listing rule as resources; invalid name AND missing args both map to `-32602`; a porter who confuses `resource_link` (by reference) with embedded `resource` (by value), or who varies the prompt list per connection, breaks the contract.

**Probe:** no runtime tests in the spec repo; machine-checkable anchors are the `Prompt*`/`ResourceLink`/`EmbeddedResource` wire types + `scripts/validate-examples.ts`. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "GetPromptResult|PromptMessage|ResourceLink|EmbeddedResource", limit: 10 });
```

## Verdict
Adopt the two-request surface (`list` / `get`), the user-controlled interaction model, connection-stable listings, `-32602` for unknown names/missing args, and the by-reference vs by-value split between `resource_link` and embedded `resource`; adapt your template catalog and rendering to host; omit model-controlled invocation of prompts (that's tools) and stdio-specific behavior.
