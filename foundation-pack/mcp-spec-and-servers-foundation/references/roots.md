<!-- capsule-v2 -->
# Roots (roots/list) — how does a server ask the client for the filesystem roots it may operate on?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What is the `roots/list` request/result contract, and why is it deprecated in favor of passing directories/files via tool parameters?

## Server-requested roots via MRTR
**Path/Symbol:** `docs/specification/draft/client/roots.mdx` (whole; deprecation :7–17; user interaction :26–36; capabilities :38–51; protocol messages :53–79; flow :81–92; data types :94–128; error handling :130–134; security :135–147; implementation :148–159); wire types `schema/draft/schema.ts` (`ListRootsRequest` :2718–2723, `ListRootsResult` :2742–2744, `Root` :2758–2775).

**Deprecation:** Roots is **deprecated** as of protocol `2026-07-28` (SEP-2577); remains in the spec ≥12 months; new implementations SHOULD NOT adopt it — migrate to passing directories/files via tool parameters, resource URIs, or server configuration.

**Data Shape:** roots are informational guidance, **not** an access-control mechanism — the protocol does not enforce that servers stay within roots. A `Root` = `{ uri: string (must start with file://), name?: string }`.

**Capabilities:** clients supporting roots MUST declare `roots` in `_meta.io.modelcontextprotocol/clientCapabilities` on each request: `{ "roots": {} }`.

### Decisive source
```jsonc
// roots.mdx:57-79 (request + result)
// Server -> Client, inside InputRequiredResult.inputRequests:
{ "method": "roots/list" }
// Client -> Server, inside inputResponses on the retried request:
{ "roots": [ { "uri": "file:///home/user/projects/myproject", "name": "My Project" } ] }
```

**Flow (MRTR):** client → `tools/call(id: 1)` → server needs roots → server responds `InputRequiredResult(roots/list)` → client returns roots inside `inputResponses{key: roots}` + `requestState` on the retried `tools/call(id: 2)`. The `Root.uri` MUST be a `file://` URI in the current spec.

**Error handling:** if an error occurs, the client does not need to replay the initial call with an error message — the server is not waiting for a response with the `InputRequiredResult` pattern.

**Security:** clients MUST only expose roots with appropriate permissions, validate all root URIs to prevent path traversal, implement proper access controls, and monitor root accessibility. Servers SHOULD handle roots becoming unavailable, respect root boundaries during operations, and validate all paths against provided roots.

**Implementation:** clients SHOULD prompt users for consent before exposing roots, provide clear UIs for root management, validate root accessibility before exposing, and monitor for root changes. Servers SHOULD check for the roots capability before usage, respect root boundaries, and cache root information appropriately.

**Invariant:** roots are advisory, not enforcement — a porter who treats roots as a security boundary (or who doesn't validate root URIs against path traversal) gets the model wrong. The `file://`-only URI restriction is a hard constraint in the current spec.

**Probe:** no runtime tests in the spec repo; wire types (`ListRootsRequest`/`ListRootsResult`/`Root`) + `scripts/validate-examples.ts` are the machine-checkable anchors. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "ListRootsRequest|ListRootsResult", limit: 10 });
```

## Verdict
Adopt the `roots/list` MRTR contract and the advisory-not-enforcement semantics if you must interoperate with legacy roots; adapt root URI validation and consent UX to host; **omit** for new implementations (deprecated SEP-2577 — pass directories/files via tool parameters, resource URIs, or server configuration instead).
