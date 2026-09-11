<!-- capsule-v2 -->
# File-part resolution ladder — how do @file, data:, MCP-resource, and agent parts become transcript text?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** What does each file-part protocol branch produce — and why is a FAILED read still a successful prompt?

## Protocol-switched part expansion
**Path/Symbol:** `packages/opencode/src/session/prompt.ts` (`createUserMessage`/`resolvePart`, lines 699–993; MCP resource :702–784; data: :786–807; file: :808–970; agent :974–990).
**Signature:** `resolvePart(part): Effect<Draft<SessionV1.Part>[]>` — one input part fans out to MANY stored parts.
**Data Shape:** Branch keys: `part.source?.type === "resource"` (MCP) vs `new URL(part.url).protocol`. Limits: `MAX_MCP_RESOURCE_BLOB_BYTES = 10MiB`; attachment MIME allowlist {application/pdf, image/gif, image/jpeg, image/png, image/webp}; base64 size computed from string length with padding math (`mcpResourceBase64Size`). Text files route through the REAL Read tool (`execRead`) with LSP symbol fallback when `start===end`.

### Decisive source
```ts
// prompt.ts:734-752 — unsupported/oversize binaries degrade to EXPLANATORY TEXT
if (!SUPPORTED_MCP_RESOURCE_ATTACHMENT_MIMES.has(mime)) {
  pieces.push({ ... type: "text", synthetic: true,
    text: `[Binary MCP resource omitted: ${filename ?? uri} (${mime}, ${formatMcpResourceBytes(size)}) is not a supported attachment type]` })
  continue }
if (size > MAX_MCP_RESOURCE_BLOB_BYTES) {
  pieces.push({ ... text: `[Binary MCP resource omitted: ... exceeds ${formatMcpResourceBytes(MAX)}]` })
  continue }
// prompt.ts:890-905 — Read-tool failure becomes an error NARRATIVE part, prompt still succeeds
pieces.push({ type: "text", synthetic: true,
  text: `Read tool failed to read ${filepath} with the following error: ${message}` })
```

**Flow:** unbounded-concurrency fan-out per part → file: + text/plain ⇒ synthesize "Called the Read tool with the following input: {...}" + execute real read (range params via URL ?start&end; `start===end` resolves through `lsp.documentSymbol` to expand a line number into the enclosing symbol range) → success appends output (+attachments or original file part); directory mime ⇒ read listing; other mimes ⇒ base64 data-url file part → MCP resources ⇒ synthetic "Reading MCP resource" header then per-content-item text/blob pieces with omit-notices for disallowed MIME/>10MiB → agent parts keep the part + append "call the task tool with subagent:" directive, adding ". Invoked by user; guaranteed to exist." hint when permission pre-evaluates to deny → plugin `chat.message` trigger sees resolvedParts → image/* parts go through `image.normalize` (ResizerUnavailable tolerated) → schema decode of every part logs-but-continues on invalid shapes → persist.
**Invariant:** Resolution failures NEVER fail the user message — every failure mode converts to a visible synthetic text part ("Read tool failed…", "Failed to read MCP resource …", omission notices). The model must be able to see WHY content is missing. Stored order stays deterministic even though resolution is concurrent (flat-map preserves input order).
**Probe:** `packages/opencode/test/session/prompt.test.ts:2105` missing-file ⇒ "Read tool failed to read" present; `:2141` "keeps stored part order stable when file resolution is async" (text[0]=Called-the-Read, text[1]=failure, text[2]="after-file"); `:2185` `#` in filename round-trips via %23 URL; `:2068/:2035` interrupt propagation into execRead for file AND directory parts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", qn_pattern: "packages.opencode.src.session.prompt", limit: 20, detail: "ids" });
await mcp.codebase_memory.search_graph({ project: "opencode", query: "resolvePromptParts", limit: 5 });
```

## Verdict
Adopt fail-open narrative errors, the omit-notice vocabulary, order-stable fan-out, and LSP line→symbol expansion; adapt Read/LSP service calls; omit literal notice strings if host has its own UX.
