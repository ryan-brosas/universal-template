<!-- capsule-v2 -->
# Payload/method decoupling — how should a protocol define messages to support transports beyond JSON-RPC?

**Source:** modelcontextprotocol/specification MIT `main@57ac4a2e`; Codebase Memory `modelcontextprotocol`. **Question:** When porting MCP (or designing a similar RPC protocol) so it can bind to transports other than JSON-RPC, how should request/response message types be structured?

## Standalone named payload schemas (SEP-1319, Final)
**Path/Symbol:** `seps/1319-decouple-request-payload-from-rpc-methods-definiti.md` (whole; principle :25; proposed shape :45–64; layer split :70–77; backward-compat :79–82); reflected in wire types `schema/draft/schema.ts` (`CallToolRequestParams` :1863, `CallToolRequest.params: CallToolRequestParams` :1884, `CallToolResultResponse.result: CallToolResult | InputRequiredResult` :1848–1849).

**Data Shape:** every structure used as an RPC `params` or `result` is defined as a STANDALONE, named top-level schema (e.g. `CallToolRequestParams extends RequestParams`). The RPC method definition then only REFERENCES that schema (`params: CallToolRequestParams`) instead of inlining the full structure. This is the current shape of `schema.ts` — the refactoring is already applied.

### Decisive source
```ts
// seps/1319-...md:51-63 (proposed = now-shipped shape)
export interface CallToolRequestParams extends RequestParams {
  name: string;
  arguments?: { [key: string]: unknown };
}
// ...the RPC method merely references the model:
export interface CallToolRequest extends Request {
  method: "tools/call";
  params: CallToolRequestParams;
}
```

**Flow / architectural boundary:** two concerns are separated — (1) the **Data Layer**: transport-agnostic payload definitions (`CallToolRequestParams`) representing WHAT is exchanged; (2) the **Transport Layer**: the protocol-specific wrapper (`CallToolRequest`) describing HOW it is sent. A new binding (e.g. gRPC) reuses the same Data-Layer models under a different envelope, instead of maintaining a parallel per-transport spec.

**Invariant:** payloads are named independently of their RPC envelope, and this refactor is NON-BREAKING — the on-the-wire JSON is byte-identical before/after, so existing compliant clients/servers are unaffected. The decoupling is what makes multi-transport bindings feasible without forking the message models.

**Probe (deterministic, graph not connected this pass):** `grep -n "interface CallToolRequestParams\|params: CallToolRequestParams" schema/draft/schema.ts` ⇒ :1863 and :1884 at pin 57ac4a2e (standalone type + reference), confirming the SEP is reflected in the source-of-truth schema.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "CallToolRequestParams|CallToolRequest|Data.Layer|Transport.Layer", limit: 10 });
```

## Verdict
Adopt the data-layer/transport-layer split when porting MCP to a non-JSON-RPC binding or generating code from the schema: keep every `params`/`result` as a standalone named schema referenced by the RPC wrapper, never inline the payload into the method definition. This preserves the wire format exactly while enabling new transports to reuse the same message models. Omit nothing — the split is already the shipped shape of `schema.ts`, so matching it keeps you aligned with future bindings.
