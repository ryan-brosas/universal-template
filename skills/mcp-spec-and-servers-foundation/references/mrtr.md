<!-- capsule-v2 -->
# Multi Round-Trip Requests (MRTR) — how does a stateless server ask the client for sampling/elicitation/roots mid-operation?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What is the exact respond-retry loop that replaces server-initiated requests, and which `requestState` integrity rules keep it safe?

## InputRequiredResult ⇒ client retries with inputResponses + a NEW id
**Path/Symbol:** `docs/specification/draft/basic/patterns/mrtr.mdx` (whole pattern; core types :54–180; supported requests :182–192; server requirements :224–247; client requirements :249–257; security :269–272); wire types `schema/draft/schema.ts` (`InputRequest` :537–538 = CreateMessageRequest | ListRootsRequest | ElicitRequest; `InputRequests` map :553–555; `InputResponses` :567–569; `InputRequiredResult` :584–595 — `inputRequests?`, `requestState?: string`; `InputResponseRequestParams` :600–609 adds optional `inputResponses`+`requestState` to any client request params).

### Decisive source
```md
# mrtr.mdx:245-256 (the loop's rules)
1. Servers MUST include at least one of inputRequests or requestState in
   every InputRequiredResult response.
...
1. If a client request contains a requestState field, servers MUST treat
   requestState as an attacker-controlled input. If requestState influences
   authorization, resource access, or business logic, servers MUST protect
   its integrity (e.g. HMAC or AEAD) and MUST reject state that fails
   verification.
1. The JSON-RPC id MUST be different between the initial request and the
   retry, as they are independent requests.
```
`requestState` is an opaque server-authored string ("AEAD-protected blob" in examples) that the client echoes back verbatim; clients MUST NOT inspect, parse, or modify it (:130–131). Replay defenses the server SHOULD embed inside the protected payload: authenticated principal, short TTL, originating-request identifier (method + digest of salient params); these bound but do not guarantee single-use — one-time redemptions MUST be enforced server-side (:234–243).

**Flow:** client POSTs `tools/call|resources/read|prompts/get` (id: 1) → server lacks info → responds `InputRequiredResult{resultType: "input_required", inputRequests: {serverAssignedKey: ElicitRequest|CreateMessageRequest|ListRootsRequest}, requestState}` → client fulfills each keyed request → retries the ORIGINAL method (id: 2) with original params PLUS `inputResponses{key→result}` PLUS the untouched `requestState` → server reconstitutes context purely from the retry body and completes. Both steps are fully independent requests — no shared storage or sticky load balancing required.

**Hard gates:** MRTR is legal ONLY on tools/call, resources/read, prompts/get — MUST NOT on any other request (:184–192). Servers MUST NOT include an `inputRequests` entry for a capability the client hasn't declared (no elicitation capability ⇒ no elicitation/create) (:246). Servers MUST NOT assume clients will fulfill requests or retry at all; re-prompting via another InputRequiredResult is allowed. Missing requested info ⇒ re-request via new InputRequiredResult rather than erroring (:266–267); unexpected extra keys in inputResponses are ignored.

**Invariant:** the retry carries ALL context — a porter who stores half-finished tool state in server memory breaks stateless horizontal scaling, and one who trusts unverified `requestState` hands clients an authorization-forgery primitive. New JSON-RPC id per attempt is mandatory (they are independent requests).

**Probe:** no runtime tests in the spec repo; machine-checkable anchors are the schema types (`InputRequiredResult` extends Result, `CallToolResultResponse.result: CallToolResult | InputRequiredResult` schema.ts :1848–1850) and example payloads under `schema/draft/examples/InputRequiredResult/**` validated by `scripts/validate-examples.ts`. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:** (`query` BM25 now zero-hits this doc-shaped graph — noise-label filtering; use `name_pattern`):
```bash
codebase-memory-mcp cli search_graph --project modelcontextprotocol \
  --name-pattern 'InputRequiredResult|inputRequests|requestState|InputResponses' --limit 10
# → ~44 rows; e.g. InputRequests Variable schema/2026-07-28/schema.json :1297-1303
```

## Verdict
Adopt the InputRequiredResult retry loop with keyed inputRequests, opaque-but-integrity-protected requestState (HMAC/AEAD + principal + TTL + request digest), capability-gated elicitation entries, and new-id-per-attempt semantics; adapt your state serialization format and key derivation to host crypto; omit server-initiated JSON-RPC requests entirely — they are removed from this revision.
