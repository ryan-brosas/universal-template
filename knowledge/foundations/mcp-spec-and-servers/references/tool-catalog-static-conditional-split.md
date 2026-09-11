<!-- capsule-v2 -->
# Everything-server tool catalog — what do the remaining demo tools each pin about result-shape and registration mechanics (echo/env/sum/tiny-image/sampling)?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** Which per-tool contracts does the canonical test server establish that a new MCP server author will be asked to reproduce?

## One registry, two batches: static tools at construction; capability-gated tools post-initialize
**Path/Symbol:** `src/everything/tools/index.ts` (:24–40 `registerTools` — 12 static; :42–52 `registerConditionalTools` — 7 gated incl. all task tools). Per-tool files read whole this pass:
- `tools/echo.ts` (40L) + exported `EchoSchema` (:7–10) — schema-first validation, `EchoSchema.parse(args)` INSIDE the handler.
- `tools/get-env.ts` (39L) — `inputSchema: {}`, returns `JSON.stringify(process.env, null, 2)` in one text block.
- `tools/get-sum.ts` (51L) — numeric parse then compute.
- `tools/get-tiny-image.ts` (53L) — exported `MCP_TINY_IMAGE` base64 PNG constant; interleaved text/image/text blocks.
- `tools/trigger-sampling-request.ts` (97L) — SYNC sampling: gate on `clientCapabilities.sampling !== undefined`; builds `CreateMessageRequest` (messages/systemPrompt/maxTokens/temperature 0.7); `extra.sendRequest(request, CreateMessageResultSchema)`.

**Signature:** uniform registration `(server: McpServer) => void` with module-level `const name` + `config { title, description, inputSchema, annotations }`; every config carries ALL FOUR hints (`readOnlyHint/destructiveHint/idempotentHint/openWorldHint`) even when trivially false.

**Data Shape:** results are single- or multi-block `{ content }` arrays; env dump is a pretty-printed JSON string; tiny image proves base64 image blocks round-trip (`data` + `mimeType: "image/png"`).

### Decisive source
```ts
// tools/index.ts:24-52 — the static/conditional split as DATA, not convention
export const registerTools = (server: McpServer) => {
  registerEchoTool(server); registerGetAnnotatedMessageTool(server); registerGetEnvTool(server);
  registerGetResourceLinksTool(server); registerGetResourceReferenceTool(server);
  registerGetStructuredContentTool(server); registerGetSumTool(server); registerGetTinyImageTool(server);
  registerGZipFileAsResourceTool(server); registerToggleSimulatedLoggingTool(server);
  registerToggleSubscriberUpdatesTool(server); registerTriggerLongRunningOperationTool(server);
};
export const registerConditionalTools = (server: McpServer) => {
  registerGetRootsListTool(server); registerTriggerElicitationRequestTool(server);
  registerTriggerUrlElicitationTool(server); registerTriggerSamplingRequestTool(server);
  // Task-based research tool (uses experimental tasks API)
  registerSimulateResearchQueryTool(server);
  // Bidirectional task tools - server sends requests that client executes as tasks
  registerTriggerSamplingRequestAsyncTool(server); registerTriggerElicitationRequestAsyncTool(server);
};
```
```ts
// trigger-sampling-request.ts — sync sampling round-trip
const request: CreateMessageRequest = { method: "sampling/createMessage",
  params: { messages: [{ role: "user", content: { type: "text", text: `Resource ${name} context: ${prompt}` } }],
    systemPrompt: "You are a helpful test server.", maxTokens, temperature: 0.7 } };
const result = await extra.sendRequest(request, CreateMessageResultSchema);
```

**Flow:** static batch registers immediately after server construction (visible to clients before any capability exchange) → conditional batch runs inside the initialized path where `getClientCapabilities()` is live → each handler validates via its zod schema (echo/get-sum parse explicitly) or ships an intentionally empty `{}` schema (get-env/toggle tools) → sampling tool demonstrates the minimal server→client LLM round trip against the typed result schema.

**Invariants:**
1. **Capability-dependent tools NEVER join the static batch** — registering them unconditionally exposes tools whose handlers would fail without the feature (the gating capsules own the mechanics; this pins the CATALOG split).
2. **Empty input schemas are explicit `{}`, not omitted** — omission changes wire shape; `{}` declares "no arguments" honestly.
3. **All four annotation hints are always present**, letting clients render conservative defaults correctly rather than guessing from absent fields.
4. Demo env-dump tool is a DEBUG surface (readOnlyHint true) — porters must NOT ship it to production tenants as-is.

**Probe:** `src/everything/__tests__/tools.test.ts:45–534` pins echo (incl. invalid-input rejection :71–80), EchoSchema unit cases (:82–96), get-sum math/negative/float/invalid (:97–157), get-env JSON validity (:158–186), tiny-image base64 validity (:187–225), structured-content trio (:226–271), and the sampling registration gates (:535–566). Coverage caveat: no test asserts the full static-batch count (12) — deterministic source probe above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "registerTools registerConditionalTools echo get-env get-tiny-image CreateMessageRequest", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the two-batch catalog layout, explicit `{}` input schemas, always-present hint quadruple, and schema-parse-inside-handler discipline for your own server's demo/debug surfaces; adapt the catalog contents to your product; omit env dumping and fake data from anything user-facing. This capsule consolidates the seven small never-cited tools so the lane's file-level sweep is complete at symbol level.
