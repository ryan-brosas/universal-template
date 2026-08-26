<!-- capsule-v2 -->
# x-mcp-header parameter mirroring — how does a server route tool parameters into HTTP headers so intermediaries can act without parsing the body?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6` (`docs/specification/2026-07-28/server/tools.mdx` §x-mcp-header :334–403; transport rules in `docs/specification/2026-07-28/basic/transports/streamable-http.mdx` §Custom Headers from Tool Parameters :356–409). Codebase Memory `modelcontextprotocol`. **Question:** How do you designate specific tool parameters to be mirrored into `Mcp-Param-{name}` HTTP headers, and what makes an annotation invalid?

## `x-mcp-header` in the parameter's JSON Schema → `Mcp-Param-{name}` header on the call
**Path/Symbol:** `docs/specification/2026-07-28/server/tools.mdx` §x-mcp-header :334–403 (annotation + constraints + rejection rule); `docs/specification/2026-07-28/basic/transports/streamable-http.mdx` §Custom Headers from Tool Parameters :356–409 (client MUST mirror + schema-extension constraints + statically-reachable rule).

**Signature:** `x-mcp-header` is an extension property placed directly inside the JSON Schema of the parameter to mirror; its value is the name portion of the resulting `Mcp-Param-{name}` HTTP header.

**Data Shape:** e.g. a `region` string parameter annotated `"x-mcp-header": "Region"` produces header `Mcp-Param-Region: us-west1` on the `tools/call` HTTP request. This lets load balancers/proxies/WAFs route on parameter values without parsing the body.

### Decisive source
```jsonc
// 2026-07-28/server/tools.mdx :366-395 (constraints, verbatim)
// MUST NOT be empty; MUST match HTTP field-name token syntax (1*tchar, RFC 9110 §5.1);
// MUST NOT contain control chars incl. CR/LF;
// MUST be case-insensitively unique among all x-mcp-header values in the inputSchema;
// MUST only apply to primitive-typed params (integer, string, boolean) — number NOT permitted;
//   integer values MUST be within IEEE754 safe range (−2^53+1 .. 2^53−1);
// MUST only apply to properties STATICALLY REACHABLE from the schema root:
//   reachable via a chain of ONLY `properties` keys — NOT through items/oneOf/anyOf/allOf/
//   not/if-then-else/$ref. An annotation anywhere else invalidates the tool definition.
```

**Flow:** server annotates a parameter's schema with `x-mcp-header` → client (Streamable HTTP) mirrors that parameter's value into the `Mcp-Param-{name}` header on the `tools/call` POST → intermediary routes/processes on the header → server validates the mirrored header against the body (per the existing `-32020` header-mirroring contract in `streamable-http.md`). If no value is present at the annotated property path in the call arguments, the header is omitted.

**Invariant:** **clients MUST reject malformed annotations — and rejection is per-tool, not fatal.** "Clients using the Streamable HTTP transport MUST reject tool definitions where any `x-mcp-header` value violates these constraints. Rejection means the client MUST exclude the invalid tool from the result of `tools/list`. Clients SHOULD log a warning... This ensures that a single malformed tool definition does not prevent other valid tools from being used." (tools.mdx :402–407). Clients on other transports (stdio) MAY ignore `x-mcp-header` entirely. The statically-reachable rule is the subtle one: an annotation buried under `oneOf`/`items`/`$ref` is invalid, not silently ignored. And a security MUST: **servers SHOULD NOT mark sensitive parameters (passwords, API keys, tokens, PII) with `x-mcp-header`**, because header values are visible to network intermediaries (tools.mdx :400).

**Probe:** no runtime test in the spec repo (docs+SEP only — coverage caveat). Deterministic: the constraint list and example are machine-checkable in `tools.mdx` :334–403 and the transport section :356–409; the `Mcp-Param-{name}` header family is already pinned in `streamable-http.md` (intermediaries that don't recognize `Mcp-Param-*` MUST forward them).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "x-mcp-header|Mcp-Param", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt `x-mcp-header` annotations for routing-relevant, non-sensitive primitive tool parameters so intermediaries can act on them without parsing bodies; enforce the statically-reachable/primitive-only/uniqueness constraints and per-tool rejection on the client; adapt the header-name mapping and your routing topology to host; omit annotating secrets (header values are visible to intermediaries). Complements `streamable-http.md` (the `Mcp-Param-*`/`-32020` mirroring contract this rides on).
