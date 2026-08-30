<!-- capsule-v2 -->
# MCP tool parameter headers — how do tool arguments become HTTP headers without injection?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** The 2026-07-28 MCP spec mirrors request metadata into headers — what validation ladder makes an `x-mcp-header` annotation safe to translate into an `Mcp-Param-*` header?

## Annotation scan → binding table → typed header emission
**Path/Symbol:** `packages/mcp/src/tool/mcp-http-headers.ts` — `getMCPToolHeaderBindings` (:35–114), `createMCPToolHeaders` (:131–160), `encodeMCPHeaderValue` (:18–33).
**Signature:** `getMCPToolHeaderBindings(inputSchema: unknown) => {success:true, bindings:{headerName,path,valueType}[]} | {success:false, error:string}`; `createMCPToolHeaders({bindings,args}) => Record<string,string>`.
**Data Shape:** Bindings record the property PATH, declared type (`boolean|integer|string`), and header token; emitted header names are prefixed `Mcp-Param-`.

### Decisive source
```ts
if ('x-mcp-header' in value) {
  if (!staticallyReachable || path.length === 0)
    { error = 'x-mcp-header is not on a statically reachable property'; return; }
  if (typeof headerName !== 'string' || !HTTP_TOKEN_PATTERN.test(headerName))
    { error = 'x-mcp-header must be a non-empty HTTP token'; return; }   // RFC token charset
  const normalized = headerName.toLowerCase();
  if (headerNames.has(normalized)) { error = `... not unique`; return; } // case-insensitive dedupe
  if (valueType !== 'boolean' && valueType !== 'integer' && valueType !== 'string')
    { error = 'can only annotate boolean, integer, or string properties'; return; }
}
// recursion keeps staticallyReachable ONLY through 'properties' children;
// every other branch descends with staticallyReachable=false (conditional/oneOf/anyOf unreachable)
...
headers[`Mcp-Param-${binding.headerName}`] = encodeMCPHeaderValue(String(value));
```

**Flow:** walk schema once → validate each annotation (reachability → token charset → uniqueness → allowed types) collecting bindings or ONE fatal error string → at call time resolve each path in args, skip nullish values, TypeError on runtime type mismatch, encode value. Encoding: plain ASCII (tab+0x20–0x7e), trim-stable, not already base64-sentinel passes through; anything else becomes `=?base64?<b64>?=` so non-ASCII or hostile values can't forge header structure.
**Invariant:** Only STATICALLY reachable properties may bind (no conditional-schema smuggling), header tokens must match the RFC token grammar, names dedupe case-insensitively, and runtime values re-validate against the declared type before hitting the wire.
**Probe:** deterministic probes: `grep -cF Mcp-Param- packages/mcp/src/tool/mcp-http-headers.ts` → `1`; `grep -cF '=\\?base64\\?' …ts` → `1`. Direct tests: `mcp-http-headers.test.ts` (136 lines, added with #19029).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "getMCPToolHeaderBindings x-mcp-header", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 getMCPToolHeaderBindings :35-114, #2 encodeMCPHeaderValue :18-33
```

## Verdict
Adopt the four-check ladder + static-reachability invariant + base64 sentinel encoding; adapt the `Mcp-Param-` prefix only with your server implementation; omit nothing — dropping reachability checking lets `(anyOf)` branches inject arbitrary headers.
