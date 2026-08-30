<!-- capsule-v2 -->
# License fetch-failure classification — how do you tell an operator WHY an outbound HTTPS call died behind a corporate proxy?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** A self-hosted instance validates its license over HTTPS; when that call throws (TLS interception, dead DNS, timeout), how does the error reach the operator as an actionable diagnosis instead of a bare internal-error toast?

## Thrown-fetch taxonomy: timeout / tls-with-remedy / network / verbatim rethrow
**Path/Symbol:** `apps/web/src/features/licensing/mutations.ts:describeFetchFailure` (lines 35–73), `TLS_ERROR_CODE_PATTERN` (line 32), `LicenseManager.validateLicenseKey` catch arm (lines 117–135); direct test `features/licensing/mutations.test.ts` (lines 86–152).
**Signature:** `describeFetchFailure(error: unknown) → { reason: "timeout"|"tls"|"network", code: string, message: string } | null`; `validateLicenseKey(input) → parsed license | throws AppError(INTERNAL_SERVER_ERROR) | rethrows`.
**Data Shape:** Node's thrown fetch is `TypeError("fetch failed")` with the real cause on `error.cause.code`; timeouts arrive as `DOMException` with `name === "TimeoutError"`; a 30s `AbortSignal.timeout` bounds the call (line 23).

### Decisive source
```ts
const TLS_ERROR_CODE_PATTERN =
  /^(CERT_|DEPTH_ZERO_|SELF_SIGNED_|UNABLE_TO_(GET|VERIFY)_|ERR_TLS_)/;

function describeFetchFailure(error: unknown) {
  if (error instanceof DOMException && error.name === "TimeoutError") {
    return { reason: "timeout", code: "TIMEOUT", message: `...did not respond within ${REQUEST_TIMEOUT_MS}ms.` };
  }
  // Only "fetch failed" carries a transport fault. Other TypeErrors are
  // programming or configuration faults — a malformed LICENSE_API_URL throws
  // "Failed to parse URL from ..." — and reporting those as connectivity would
  // send an operator to debug a network that is working fine.
  if (error instanceof TypeError && error.message === "fetch failed") {
    const code = (error.cause as { code?: string } | undefined)?.code;
    if (code && TLS_ERROR_CODE_PATTERN.test(code)) {
      return { reason: "tls", code, message: "...point NODE_EXTRA_CA_CERTS at your root CA certificate and restart." };
    }
    return { reason: "network", code: code ?? "UNKNOWN", message: "Could not reach the licensing service." };
  }
  return null;   // → caller rethrows verbatim
}
// validateLicenseKey catch arm:
const failure = describeFetchFailure(error);
if (!failure) throw error;
logger.error({ reason: failure.reason, code: failure.code, apiUrl }, failure.message);
throw new AppError({ code: "INTERNAL_SERVER_ERROR", cause: error, message: failure.message });
```

**Flow:** POST to the licensing API with a 30s abort signal → on THROW: classify (timeout → tls → network → unclassifiable) → log reason+code+apiUrl → surface the classified message through AppError into the control-panel toast. On non-ok RESPONSE (a separate branch): parse body as JSON-or-raw-text (proxy HTML tolerated) and throw a generic validation failure. The doc comment records the incident this exists for: a TLS failure behind a TLS-intercepting proxy was indistinguishable from a dead DNS entry without `cause.code`, and before the catch arm existed the request failed with nothing logged at all.
**Invariant:** classification is conservative in both directions. Inbound: only the EXACT message "fetch failed" counts as transport — a malformed `LICENSE_API_URL` also throws TypeError but must be reported as configuration, not connectivity. Outbound: anything unclassifiable is RETHROWN VERBATIM rather than mislabelled, so a real bug never wears a "could not reach" costume. The remedy text (NODE_EXTRA_CA_CERTS) lives in the user-facing message because the toast is generic — the message is the only channel that reaches the operator.
**Probe:** direct test `features/licensing/mutations.test.ts:86–152` pins all four classes with REAL Node codes captured from badssl.com endpoints: four cert codes each expect the NODE_EXTRA_CA_CERTS hint (:107–117), ENOTFOUND expects "Could not reach" and NOT the cert hint (:120–125), TimeoutError expects "did not respond" (:127–133), RangeError rethrown by identity (:135–140), and a non-transport TypeError (`ERR_INVALID_URL`) rethrown by identity (:142–150). Runner caveat: vitest not executable in this checkout (no node_modules) — suite read as source.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "describeFetchFailure validateLicenseKey", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-way taxonomy (timeout / tls-with-remedy / network / verbatim-rethrow) for ANY operator-facing outbound call from a self-hosted product — the exact-message gate on "fetch failed" and the verbatim rethrow are the two details that keep it honest. Adopt putting the fix instruction inside the error message when your UI's error surface is a generic toast. Adapt the TLS code pattern to your runtime's actual codes (capture them from badssl.com-style fixtures, as the test does — do not guess). Omit the response-body branch if your API contract guarantees JSON errors. Caveat: test suite read directly, not executed (no node_modules in checkout).
