<!-- capsule-v2 -->
# Server→client request association — may a server fire sampling/elicitation/roots on its own?

**Source:** modelcontextprotocol/specification MIT `main@57ac4a2e`; Codebase Memory `modelcontextprotocol`. **Question:** Can a server initiate `sampling/createMessage`, `elicitation/create`, or `roots/list` from a background task or a standalone stream, or must they always be nested inside an originating client request?

## The association invariant (SEP-2260, Final)
**Path/Symbol:** `seps/2260-Require-Server-requests-to-be-associated-with-Client-requests.md` (whole; Abstract :11–21; transport diff :145–165; timeout :224–234; client duty :239–241); rendered twin `docs/seps/2260-*.mdx`.

**Data Shape:** three server→client request methods are constrained — `roots/list`, `sampling/createMessage`, `elicitation/create`. Each MUST carry (logically) the JSON-RPC Request Id of the originating client→server request it was triggered by (e.g. while processing `tools/call`, `resources/read`, or `prompts/get`). The operational server→client **Ping** is the single excepted method.

### Decisive source
```text
// seps/2260-...md:12-21 (Abstract)
This SEP clarifies that `roots/list`, `sampling/createMessage`, and
`elicitation/create` requests **MUST** be associated with an originating
client-to-server request (e.g., during `tools/call`, `resources/read`, or
`prompts/get` processing). Standalone server-initiated requests of these types
outside notifications **MUST NOT** be implemented.
Although not enforced in the current MCP Data Layer, logically these requests
**MUST** be associated with a valid client-to-server JSON-RPC Request Id.
The operational server-to-client **Ping** is excepted from this restriction.
```

**Flow:** client sends `tools/call` → server handler needs LLM help / more input / storage roots → server emits `sampling/createMessage` / `elicitation/create` / `roots/list` scoped to that in-flight request id → client answers inside the same request's response path (MRTR `inputRequests`). The transport diff tightens Streamable HTTP: POST-stream server messages go from **SHOULD** relate to the originating request to **MUST**; GET standalone streams may carry only notifications+pings and MUST NOT carry these three request types.

**Client duty:** a client receiving one of these three request types with NO associated outbound request SHOULD respond `-32602` (Invalid Params).

**Timeout duty (human-in-the-loop):** because a nested request extends the parent's lifetime to include the user's response time (potentially unbounded), implementers MUST size transport timeouts for human delays and SHOULD use transport-level SSE keepalive to reset LB timers; `ping` MAY supplement.

**Invariant:** server→client feature requests are REACTIVE — they exist only as a nested consequence of a client-initiated operation. A background task or a standalone GET stream firing `sampling/createMessage` / `elicitation/create` / `roots/list` is prohibited; only `ping` may be unsolicited.

**Probe (deterministic, graph not connected this pass):** `grep -c "in association with an originating" docs/specification/2026-07-28/client/{sampling,elicitation,roots}.mdx` ⇒ 0/0/0 at pin 57ac4a2e, while `docs/seps/2260-*.mdx` exists (13,760 B). This is the drift signature: the invariant is Final but NOT yet folded into the 2026-07-28 normative text.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "Request.Association.Requirement|Standalone.Server.Initiated|sampling.createMessage|elicitation.create|roots.list", limit: 10 });
```

## Verdict
Adopt the association invariant for any forward-compatible server: emit `sampling/createMessage` / `elicitation/create` / `roots/list` ONLY nested inside an originating client request, never from background tasks or standalone streams; keep `ping` as the sole unsolicited server→client message. Clients should reject unassociated instances with `-32602`. Note the honest caveat: this is a Final Standards-Track SEP whose MUST language is not yet present in the 2026-07-28 spec pages — adopt it now for future-proofing, but do not claim it is current normative text.
