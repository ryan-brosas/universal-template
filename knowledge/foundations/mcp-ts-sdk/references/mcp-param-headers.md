<!-- capsule-v2 -->
# SEP-2243 Mcp-Param-* header codec — how do tool arguments travel as HTTP headers without injection or type lies?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How are `x-mcp-header` schema declarations scanned, values encoded into headers, and mirrored headers validated against body arguments on the server?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/mcpParamHeaders.ts`: `scanXMcpHeaderDeclarations` (:66+), `MCP_PARAM_HEADER_PREFIX = 'Mcp-Param-'` (:33), `X_MCP_HEADER_KEY = 'x-mcp-header'` (:36), `RFC9110_TOKEN` (:56), `PERMITTED_X_MCP_HEADER_TYPES` (:65-69), encode/decode + `validateMcpParamHeaders`; server-side consumption in `createMcpHandler.serveModern` (tools/call branch).
**Signature:** `scanXMcpHeaderDeclarations(inputSchema: unknown): {valid:true; declarations:{path,headerName,type}[]} | {valid:false; reason}`; validation returns a `-32020`-shaped rejection on missing/disagreeing/malformed headers.
**Data Shape:** Declarations allowed at ANY nesting depth under a chain of `properties` keys; case-insensitively unique header names (case preserved for emission). Values: plain ASCII field values, else the RFC 2047-style sentinel `=?base64?…?=`.

### Decisive source
```ts
// The static-reachability MUST is enforced as a structural sweep: every
// position the chain MUST NOT pass through (items/additionalProperties,
// oneOf/anyOf/allOf/not, if/then/else, $defs, $ref targets within $defs) is
// visited too, and an x-mcp-header found anywhere on that path invalidates
// the schema — "an annotation anywhere else makes the tool definition invalid".
if (!reachable || path.length === 0)
    return `${pathName(path)}: x-mcp-header is only permitted on properties statically reachable via a chain of 'properties' keys …`;
// CRLF header-injection: encode produces a sentinel value with no CR/LF.
```

**Flow:** client scans advertised inputSchema → encodes each declared argument into `Mcp-Param-{Name}` (sentinel for non-safe values) AND keeps body arguments → server re-scans the registry's schema, decodes headers, and validates against body arguments pre-dispatch → mismatch/missing/malformed ⇒ 400/-32020 with the same shape as the standard-header cross-checks.

**Invariant:** Type table is closed: string/integer/boolean (+number ONLY because the published conformance referee ships number-typed parameters — discrepancy tracked upstream); object/array/null rejected. Non-finite and out-of-±2^53 integers are REFUSED rather than stringified (a lie in the wire value). Decode rejects bad base64 padding/alphabet. Only applied when the factory returns an McpServer — a low-level Server has no registry to validate against.

**Probe:** `packages/core-internal/test/shared/mcpParamHeaders.test.ts` :57 ("CRLF header-injection: … round-trips intact"), :74/:78 (sentinel decode refusals), :89/:90 (non-finite / out-of-range refused); end-to-end mirror via `packages/client/test/client/mcpParamMirroring.test.ts`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "scanXMcpHeaderDeclarations validateMcpParamHeaders decodeMcpParamValue", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt structural-sweep reachability enforcement + sentinel encoding + mirror-validation for header-carried parameters; adapt the type table to your spec pin; omit conformance-compat quirks once upstream resolves them.
