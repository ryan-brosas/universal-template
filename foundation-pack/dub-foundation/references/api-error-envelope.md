<!-- capsule-v2 -->
# API error envelope — one handler that maps every thrown error to code/status/doc_url

**Source:** dub AGPL-3.0-or-later (EE dirs separately licensed) `main@873edc5a9727317513c966b8d9b9171794fc89f8`; Codebase Memory `dub`. **Question:** How do you turn heterogeneous thrown errors (zod, domain, ORM) into one stable, documented API error shape without leaking internals?

## DubApiError / handleApiError
**Path/Symbol:** `apps/web/lib/api/errors.ts:DubApiError` (44–61), `handleApiError` (93–159), `fromZodError` (65–91), `errorSchemaFactory` (169–213).
**Signature:** `new DubApiError({ code, message, docUrl? })`; `handleApiError({ error, workspace?, partner? }): ErrorResponse & { status }`; `handleAndReturnErrorResponse(err, headers?): NextResponse`.
**Data Shape:** wire shape is always `{ error: { code, message, doc_url? } }`. `code` is a closed zod enum (`bad_request`, `unauthorized`, `forbidden`, `exceeded_limit`, `not_found`, `conflict`, `invite_pending`, `invite_expired`, `unprocessable_entity`, `rate_limit_exceeded`, `internal_server_error`) whose numeric HTTP status lives in the SAME module (`ErrorCodes[code]`).

### Decisive source
```ts
if (error instanceof z.ZodError) return { ...fromZodError(error), status: 422 };  // first issue only (maxErrors:1)
if (error instanceof DubApiError)
  return { error: { code: error.code, message: error.message, doc_url: error.docUrl },
           status: ErrorCodes[error.code] };
if (error.code === "P2025")                       // Prisma record-not-found -> 404 not_found
  return { error: { code: "not_found", message: error?.meta?.cause || ..., }, status: 404 };
// Fallback: UNHANDLED errors are not user-facing — never expose the actual error
return { error: { code: "internal_server_error",
                  message: "An internal server error occurred. ..." }, status: 500 };
```

**Flow:** throw sites construct `DubApiError` with a closed-enum code; the doc anchor is derived automatically (`docErrorUrl + "#" + code.replace("_","-")`) unless overridden. The single catch-all handler orders checks Zod → DubApiError → Prisma P2025 → generic fallback, logs to Axiom with optional workspace/partner ids, and flushes via Next's `after()`. The same codes drive OpenAPI error responses through `errorSchemaFactory`, which stamps `x-speakeasy-name-override` so generated SDK clients get typed exception classes.
**Invariant:** unhandled errors NEVER leak their message to clients (generic fallback text); every error response carries a stable machine code that maps 1:1 to both an HTTP status and a docs anchor; zod validation reports at most one issue in object-notation paths.
**Probe:** no direct unit test on `errors.ts` itself (vitest suites cover analytics/webhooks). Source-grounded probe: `search_graph` resolves `handleApiError` and `DubApiError`; port with your own test asserting P2025 → 404/not_found and unknown Error → 500/generic text.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "handleApiError DubApiError fromZodError", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the closed-code error class + central mapper ordering (Zod → domain → ORM-not-found → opaque fallback) and the code→status/docs-anchor derivation; adapt the code enum, ORM error codes (P2025 is Prisma), and log sink. Omit the Speakeasy SDK-generation metadata unless you generate client SDKs from OpenAPI. Caveat: no direct upstream test for this seam.
