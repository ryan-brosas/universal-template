<!-- capsule-v2 -->
# tools/call validation funnel — how does the low-level Server validate tool requests/results era-exactly while staying era-blind to authors?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How do you validate a `tools/call` request and result against the RIGHT wire schema when one instance may serve two protocol eras?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/server.ts`: `_wrapHandler` tools/call branch (:514-557), `_servedModernEra()` (:567-569), `projectCallToolResult` public codec window (:1007-1012).
**Signature:** `(request, ctx) => Promise<Result>` wrapper resolving `codecForVersion(this._negotiatedProtocolVersion)` at DISPATCH time.
**Data Shape:** `codec.validateRequest/validateResult('tools/call', …)` → discriminated `{ok:true,value} | {ok:false,reason:'not-in-era'|'invalid',message}`.

### Decisive source
```ts
const codec = codecForVersion(this._negotiatedProtocolVersion);
const validatedRequest = codec.validateRequest('tools/call', request);
if (!validatedRequest.ok) {
    throw new ProtocolError(
        validatedRequest.reason === 'not-in-era' ? ProtocolErrorCode.InternalError : ProtocolErrorCode.InvalidParams,
        ...);   // not-in-era here is an INTERNAL ERROR: the era gate guarantees tools/call exists on the serving era
}
...
// v1-parity authoring affordance, era-independent: content-less result normalizes
// to content: [] BEFORE era validation. Other families stay un-normalized and fail loudly.
const normalizedResult = normalizeContentlessToolResult(result);
const validationResult = codec.validateResult('tools/call', normalizedResult);
```

**Flow:** dispatch-time codec resolution → request schema validation (era registry entry IS the plain CallToolResult schema, no widened unions) → handler via the input-required seam → input-required returns pass through untouched (CallToolResult schema does not apply) → content-less normalization → result schema validation → validated value returned. `McpServer`'s built-in handler routes its final shape through `projectCallToolResult(result, tool.outputSchemaJson)` — the ONE exposed codec function (SEP-2106 §4.3 TextContent auto-append + 2025-era `{result:…}` wrap); low-level authors call it themselves so the projection lives in the codec and handlers stay era-blind.

**Invariant:** Validation keys off the INSTANCE's negotiated version, not the request's claimed era — the edge classified the request before an instance existed. `normalizeContentlessToolResult` applies only to the tools/call family: a foreign-family body with explicit `content: undefined` or another family's shape must FAIL loudly, not silently normalize. Cache hints attach only to complete results (`attachCacheHintFallback`, never serialized; 2025 responses unaffected).

**Probe:** `packages/server/test/server/server.test.ts` :193 ("structured-only defaults to content: [] on the wire (v1 parity)"), :204 ("array result rejected loudly"), :211 ("foreign body with explicit content:undefined NOT normalized"), :221 ("another result family rejected"), :231 ("authored-content passes through"); `packages/server/test/server/cacheHints.test.ts` (per-operation vs per-resource field-by-field precedence).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "_wrapHandler normalizeContentlessToolResult projectCallToolResult codecForVersion", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt dispatch-time codec resolution + family-scoped normalization + single-projection-window design; adapt the error-code mapping table; omit the WireCodec internals (core-internal plane, other capsules).
