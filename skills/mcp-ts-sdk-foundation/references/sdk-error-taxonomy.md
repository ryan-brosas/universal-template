<!-- capsule-v2 -->
# Typed SDK error taxonomy — how do local (never-wire) errors stay distinct from JSON-RPC protocol errors?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Which failure vocabulary belongs to the SDK-internal surface, and which codes cross the wire — and what keeps the two from being confused?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/errors/sdkErrors.ts`: `SdkErrorCode` enum (:8-100) with per-member semantics docblocks; `SdkError`/`SdkHttpError` classes; contrast class `ProtocolErrorCode` (`types/enums.ts`, numeric JSON-RPC codes).
**Signature:** `enum SdkErrorCode { NotConnected, AlreadyConnected, NotInitialized, CapabilityNotSupported, RequestTimeout, ConnectionClosed, SendFailed, InvalidResult, UnsupportedResultType, InputRequiredRoundsExceeded, ListPaginationExceeded, MethodNotSupportedByProtocolVersion, EraNegotiationFailed, ClientHttp*, … }`.
**Data Shape:** Descriptive STRING codes for developer experience (vs numeric ProtocolErrorCode). `data` payloads are documented per member (`{rounds,lastResult}`, `{method,listMaxPages}`, `{method,era}`, `{status,statusText,text}` on SdkHttpError).

### Decisive source
```ts
// These errors are thrown locally by the SDK and are never serialized as
// JSON-RPC error responses.
MethodNotSupportedByProtocolVersion = 'METHOD_NOT_SUPPORTED_BY_PROTOCOL_VERSION',
// … Raised locally, BEFORE anything reaches the transport.
EraNegotiationFailed = 'ERA_NEGOTIATION_FAILED',
// Negotiation-phase only: never used once an era is established. Auth walls
// never carry it … so era-recovery flows keyed on this code can never persist
// a verdict for an unauthorized exchange.
```

**Flow:** outbound era gate → typed SdkError before transport; probe failures → EraNegotiationFailed ONLY for genuine negotiation dead ends; 401/403 → ClientHttpAuthentication/ClientHttpForbidden (distinct codes so hosts can route recovery); driver caps → InputRequiredRoundsExceeded carrying the last payload for manual resume.

**Invariant:** The local/wire split is absolute: numeric −32601/−32022 etc. are PROTOCOL answers; string SdkErrorCodes never serialize onto a wire response. Recovery flows key on specific members (era-recovery on EraNegotiationFailed's exclusivity; fleet verdict caches on auth codes' separation). All classes are brand-stamped for cross-bundle instanceof (see cross-bundle-brands capsule).

**Probe:** `packages/core-internal/test/errors/crossBundleBrand.test.ts` (class identity incl. SdkError hierarchy); code-specific pins across eraGates/responseCache/inputRequired suites cited in sibling capsules.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "SdkErrorCode SdkHttpError EraNegotiationFailed", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt a two-vocabulary error design (local string codes vs wire numeric codes) with data payloads sized for recovery; adapt member list; omit HTTP-client members if you have no fetch transport.
