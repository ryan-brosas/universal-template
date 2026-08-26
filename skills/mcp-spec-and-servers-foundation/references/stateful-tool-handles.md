<!-- capsule-v2 -->
# Stateful tools via explicit handles (SEP-2567, Final) — how does a server maintain cross-call state when the protocol has no session?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6` (`seps/2567-sessionless-mcp.md`; normative-adjent guidance in `docs/specification/2026-07-28/server/tools.mdx` §Stateful Tools :683–737). Codebase Memory `modelcontextprotocol`. **Question:** With no protocol-level session, how does a server relate one tool call to the next without breaking the stateless wire contract?

## Server-minted state handles threaded through tool calls replace implicit session state
**Path/Symbol:** `seps/2567-sessionless-mcp.md` (whole SEP: abstract :1–30, rationale :31–50, design); `docs/specification/2026-07-28/server/tools.mdx` §Stateful Tools :683–737 (non-normative guidance: handle pattern + four design considerations).

**Signature:** n/a — tool-design pattern, not a wire construct. **There is no schema or wire format for a handle** — it is an ordinary string in a tool result and an ordinary argument to a later tool call.

**Data Shape:** a creation tool returns an opaque handle (e.g. `structuredContent: { "basket_id": "bsk_a1b2c3" }`); subsequent tools accept that handle as a required argument and look up server-side state under it. The model is responsible for carrying the handle forward.

### Decisive source
```jsonc
// 2026-07-28/server/tools.mdx :699-716 (the pattern, verbatim shape)
// → tools/call
{ "name": "create_basket", "arguments": {} }
// ← result
{ "content": [{ "type": "text", "text": "Created basket bsk_a1b2c3" }],
  "structuredContent": { "basket_id": "bsk_a1b2c3" } }
// → tools/call
{ "name": "add_item", "arguments": { "basket_id": "bsk_a1b2c3", "sku": "..." } }
```

**Flow:** server exposes a creation tool that mints a handle and stores state under it → returns the handle (dual text + structuredContent so both plain and typed clients see it) → the model threads it through subsequent calls → server looks state up by handle on each call. Because the protocol has no session, a server cannot rely on implicit per-connection state to relate calls.

**Invariant:** **a handle is a name, not a capability.** Design rules (tools.mdx :718–737): (1) **Authorization** — for authenticated servers, validate the caller's authorization against the handle on EVERY call; for unauthenticated servers the handle is necessarily a bearer token, so generate it with sufficient entropy (e.g. UUIDv4) and a bounded lifetime. (2) **Opacity** — opaque identifiers resist parsing/guessing; handles that encode internal structure invite abuse. (3) **Lifetime** — because handles outlive any single connection, state the retention policy in the creation tool's description (e.g. "baskets expire after 24 hours of inactivity") so the model can see it when deciding to create state. (4) **Expiry errors** — a call against an expired/unknown handle should return a **tool execution error** that says so (per `validation-error-taxonomy.md`), so the model can recover by creating a new one. This is the modern replacement for the removed `Mcp-Session-Id` session (SEP-2567/2575): list endpoints become cacheable across what used to be session boundaries, and the model decides what is shared vs isolated.

**Probe:** no runtime test in the spec repo (docs+SEP only — coverage caveat). Deterministic: the reference servers exercise the pattern — e.g. `src/memory`'s `create_entities` returns the created entities (the "handle") and later tools take names as arguments; `src/everything` session-toggle tools key state on raw `sessionId` arguments rather than any protocol session.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "Stateful Tools handle basket_id sessionless", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt explicit server-minted handles threaded through tool calls (create returns the handle, later tools take it as an argument) for ANY cross-call state — shopping carts, open browser contexts, DB transactions — instead of relying on implicit session state; adapt handle entropy/lifetime/authorization to your threat model (bearer-token semantics for unauthenticated servers); omit any attempt to reintroduce a protocol-level session. Complements `validation-error-taxonomy.md` (expired-handle errors ride `isError`) and `modern-era-lifecycle.md` (no session ⇒ this pattern is mandatory).
