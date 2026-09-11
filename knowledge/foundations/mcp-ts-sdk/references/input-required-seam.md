<!-- capsule-v2 -->
# Input-required serving seam — how does one handler serve both the 2026 input_required vocabulary and 2025 clients that cannot express it?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Where does a multi-round-trip return get validated, era-routed, and — for legacy clients — fulfilled server-side without rewriting the handler?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/server.ts`: `_invokeInputRequiredCapableHandler` (:591-697), `INPUT_REQUIRED_CAPABLE_METHODS` (:73), `_verifyRequestState` (:705-719), `_inputRequestCapabilityView` (:727-731).
**Signature:** `private async _invokeInputRequiredCapableHandler(method, handler, request, ctx): Promise<Result>`; capable set = `{'tools/call','prompts/get','resources/read'}`.
**Data Shape:** InputRequiredResult = `{inputRequests: Record<key, embedded request>, requestState?: string}` (at least ONE of the two).

### Decisive source
```ts
if (!servedModern) {
    if (!this._inputRequiredServing.legacyShim) { throw /* pre-shim loud failure */ }
    // Write-once handlers served to deployed 2025 clients:
    return await this._legacyInputRequiredShim().fulfill(method, handler, request, ctxForHandler, result);
}
// F7 at-least-one re-check (hand-built results are legal; the rule is re-checked at the seam)
const hasInputRequests = inputRequests != null && Object.keys(inputRequests).length > 0;
const hasRequestState = typeof result.requestState === 'string';
if (!hasInputRequests && !hasRequestState) throw new ProtocolError(InternalError, ...);
// then per-embedded-request capability check against the REQUEST's own envelope (-32021 on violation)
```
And the era-frozen throw:
```ts
if (error instanceof ProtocolError && error.code === ProtocolErrorCode.UrlElicitationRequired) {
    if (!servedModern) throw error;               // 2025-era: -32042 reaches the wire byte-exact
    throw new ProtocolError(InternalError,        // 2026-era: -32042 is NOT on this wire; steer loudly
      "...return inputRequired({ inputRequests: { …: inputRequired.elicitUrl(...) } } ...");
}
```

**Flow:** requestState type gate (non-string non-undefined ⇒ frozen `-32602 invalid_request_state`) → verify hook → handler → UrlElicitationRequiredError catch (era-split) → plain result passthrough → legacy arm: shim fulfill (or loud failure when `legacyShim:false`) / modern arm: at-least-one re-check + per-key capability gate via `missingClientCapabilities(required, declared)`.

**Invariant:** Era is INSTANCE state (`_negotiatedProtocolVersion`), never a per-request consult. The seam runs ABOVE the McpServer tools/call funnel so hook failures reach the wire as real JSON-RPC errors, not `isError` tool results. Capability source differs by era: the request's own `_meta` envelope (modern) vs initialize-declared state (legacy); per-request instances with no initialize hold nothing, so gates REFUSE there. Server-bug guard: any other method returning input-required throws InternalError before mis-typing the wire.

**Probe:** `packages/server/test/server/inputRequired.test.ts` :226 ("hand-built results missing both fail loudly"), :238 ("-32021 on undeclared capability"), :291 ("legacyShim:false fails loudly"), :308 ("non-multi-round-trip methods guarded"), :342 ("2026-era -32042 throw fails LOUDLY"), :356 ("2025-era keeps exact -32042").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "_invokeInputRequiredCapableHandler INPUT_REQUIRED_CAPABLE_METHODS MissingRequiredClientCapabilityError", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt the seam placement (above handler funnels, below transport) + era-split error policy + at-least-one/capability re-checks; adapt the shim internals pointer (`legacy-input-shim.md` owns them); omit core-internal driver mechanics (client-side capsule).
