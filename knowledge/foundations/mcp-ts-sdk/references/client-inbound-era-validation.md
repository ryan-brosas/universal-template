<!-- capsule-v2 -->
# Client inbound-request era validation — how does the Client validate server→client elicitation/sampling requests and results era-exactly?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** When a registered `elicitation/create` or `sampling/createMessage` handler runs, which validator sees the request/result, how does the 2025-wire vs 2026-in-band vocabulary split work, and which failures are InternalError vs InvalidParams?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/client.ts`: `Client._wrapHandler` override (:816-945) — wraps ONLY `'elicitation/create'` (:820-892) and `'sampling/createMessage'` (:894-941); every other method returns the handler untouched (:944). Codec resolution via `codecForVersion(this._negotiatedProtocolVersion)` (:832, :901). Caller-side counterpart of tools-call-validation-funnel.md (server-side `_wrapHandler`).
**Signature:** `protected override _wrapHandler(method: string, handler: (request: JSONRPCRequest, ctx: ClientContext) => Promise<Result>): (request, ctx) => Promise<Result>`
**Data Shape:** request/result validated through the instance-era WireCodec; failure shape is a discriminated union `{ok:false, reason:'not-in-era'|…, message?}`; own capabilities read from `this._capabilities.elicitation` (form/url sub-modes + applyDefaults).

### Decisive source
```ts
// :832-836 — era-exact request validation with in-band fall-through
const codec = codecForVersion(this._negotiatedProtocolVersion);
let validatedRequest = codec.validateRequest('elicitation/create', request);
if (!validatedRequest.ok && validatedRequest.reason === 'not-in-era') {
    validatedRequest = codec.validateInputRequest('elicitation/create', request);
}
if (!validatedRequest.ok) {
    throw new ProtocolError(
        validatedRequest.reason === 'not-in-era' ? ProtocolErrorCode.InternalError : ProtocolErrorCode.InvalidParams,
        validatedRequest.reason === 'not-in-era'
            ? 'No wire schema for elicitation/create in the resolved era'
            : `Invalid elicitation request: ${validatedRequest.message}`);
}
// :847-856 — mode default + OWN-capability gating
params.mode = params.mode ?? 'form';
const { supportsFormMode, supportsUrlMode } = getSupportedElicitationModes(this._capabilities.elicitation);
if (params.mode === 'form' && !supportsFormMode) {
    throw new ProtocolError(ProtocolErrorCode.InvalidParams, 'Client does not support form-mode elicitation requests');
}
// :926-930 — result-side variant mirrors the request-side selection
const hasTools = Boolean(params.tools || params.toolChoice);
let validatedResult = codec.samplingResultVariant(hasTools, result);
if (!validatedResult.ok && validatedResult.reason === 'not-in-era') {
    validatedResult = codec.validateInputResponse('sampling/createMessage', result);
}
```

**Flow:** dispatch resolves the codec from the INSTANCE era (not per-message claims). Request side: wire validator first; `not-in-era` (the method is 2026 in-band vocabulary reached only via the multi-round-trip driver) falls through to the in-band input validator; any other failure ⇒ InvalidParams; still `not-in-era` after fall-through ⇒ InternalError ("No wire schema … in the resolved era" — a bug, not a peer fault). Elicitation: `mode` defaults to `'form'`; form/url are gated against the CLIENT'S OWN declared elicitation capabilities ⇒ InvalidParams. Result side mirrors the same selection (`validateResult` → `validateInputResponse`; sampling uses `samplingResultVariant(hasTools, …)` because the 2025 result schema depends on the REQUEST params — tools vs no tools — while the 2026 embedded response validator covers both shapes). Elicitation defaults: `applyElicitationDefaults(requestedSchema, content)` only when form + action=accept + content + requestedSchema + `applyDefaults` capability — and its errors are SWALLOWED (graceful degradation, not a protocol failure).

**Invariant:** both sides of one exchange stay on the SAME era's vocabulary (request-side selection mirrored on the result side); `not-in-era` after the fall-through is an internal invariant violation (InternalError), never reported to the peer as InvalidParams; the in-band schema fallback must NOT bypass the upstream era gate — on a modern connection a wire `elicitation/create` is dropped before any handler runs (modernEraInboundDrop), so `_wrapHandler` only ever sees in-band invocations there.

**Probe:** `packages/client/test/client/inputRequiredEngine.test.ts` :188-236 (forked tool-bearing embedded sampling response validated against the 2026 in-band response schema — non-object `structuredContent` legal only on the 2026 fork, retry carries the bare response unchanged); `packages/client/test/client/modernEraInboundDrop.test.ts` :93-128 (wire elicitation/create on a modern connection never reaches the registered handler, zero bytes written back, surfaced via onerror) and :129-144 (legacy control arm keeps answering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typescript-sdk", query: "_wrapHandler validateInputRequest samplingResultVariant", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-method-only wrap (everything else passes through) and the reason-keyed error split verbatim; adapt the capability gating if your host declares elicitation modes differently; omit any plan to validate other inbound methods here — they have no dual-era vocabulary split. Coverage caveat: the wire-side InvalidParams/InternalError throw paths themselves have no direct test in-repo (only the in-band path and the upstream drop are pinned) — port-yourself-pin those branches.
