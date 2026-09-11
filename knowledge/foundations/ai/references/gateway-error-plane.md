<!-- capsule-v2 -->
# Gateway error plane — how does any failure (HTTP, timeout, unknown) become exactly one GatewayError, and why Symbol.for markers?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the canonical funnel that turns every gateway failure mode into a typed, retryable-flagged error without double wrapping?

## Funnel: asGatewayError → createGatewayErrorFromResponse
**Path/Symbol:** `packages/gateway/src/errors/as-gateway-error.ts:asGatewayError` (30–75) + `isTimeoutError` (11–28); `create-gateway-error.ts:createGatewayErrorFromResponse` (23–138); `gateway-error.ts:GatewayError` base (10–55).
**Signature:** `async function asGatewayError(error: unknown, authMethod?: 'api-key' | 'oidc'): Promise<GatewayError>`.
**Data Shape:** Decision ladder: (1) already `GatewayError.isInstance` → return as-is; (2) undici timeout code (`UND_ERR_HEADERS_TIMEOUT`/`BODY_TIMEOUT`/`CONNECT_TIMEOUT`) on the error OR on an `APICallError.cause` → `GatewayTimeoutError`; (3) `APICallError` → extract body via `extractApiCallResponse` (`error.data` ?? secure-parsed `responseBody`?? raw string ?? `{}`) and dispatch on `error.type`; (4) anything else → synthetic 500 with message prefixed `Gateway request failed:`.

### Decisive source
```ts
// gateway-error.ts — cross-realm-safe instance check:
const symbol = Symbol.for(marker);            // 'vercel.ai.gateway.error'
private readonly [symbol] = true;
static hasMarker(error: unknown): boolean {
  return typeof error === 'object' && error !== null && symbol in error && (error as any)[symbol] === true;
}
constructor({ message, statusCode = 500, ..., isRetryable = statusCode != null &&
  (statusCode === 408 || statusCode === 409 || statusCode === 429 || statusCode >= 500) }) {
  super(generationId ? `${message} [${generationId}]` : message);
```
```ts
// create-gateway-error.ts — switch on server error.type; default is NOT a dedicated class:
case 'authentication_error': … case 'invalid_request_error': … case 'rate_limit_exceeded': …
case 'model_not_found': /* param re-validated for modelId */ …
default: return new GatewayInternalServerError({ message, statusCode, cause, generationId });
```

**Flow:** throw site (`doGenerate`/`doStream`/GET wrappers) → `asGatewayError(error, await parseAuthMethod(headers))` → typed GatewayError with `generationId` appended to the MESSAGE text and preserved as a field.
**Invariant:** Every rethrow goes through the funnel exactly once — the marker check at rung 1 makes the funnel idempotent, so nested wrappers never double-wrap. Retryability is DERIVED from status (408/409/429/5xx), not stored per class. `Symbol.for` (global registry) is deliberate: errors crossing realm/duplicate-module boundaries still match. Unknown `error.type` maps to internal-server-error, keeping the class taxonomy closed.
**Probe:** `grep -c UND_ERR_HEADERS_TIMEOUT packages/gateway/src/errors/as-gateway-error.ts` → `1`; `grep -c 'new GatewayInternalServerError' packages/gateway/src/errors/create-gateway-error.ts` → `2` (explicit case + default fallthrough). Direct tests: as-gateway-error.test.ts ('should detect error with UND_ERR_HEADERS_TIMEOUT code', 'should pass through existing GatewayError instances', cause-chain timeout test :134); create-gateway-error.test.ts ('should preserve empty string messages from Gateway').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "asGatewayError isTimeoutError UND_ERR_HEADERS_TIMEOUT", limit: 10 });
```
Resolves line-exact: `isTimeoutError Function errors/as-gateway-error.ts 11-28`, `asGatewayError Function errors/as-gateway-error.ts 30-75`.

## Verdict
Adopt the four-rung funnel + global-symbol marker + derived retryability; adapt the undici timeout codes to your HTTP client's error codes; omit the Vercel-specific remediation URLs inside authentication errors. Coverage caveat: none — the funnel is the most directly tested surface in the package (create-gateway-error.test.ts alone = 671 lines).
