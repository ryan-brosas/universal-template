<!-- capsule-v2 -->
# ajv validation funnel — how do request bodies meet swagger schemas, and which two token headers feed auth?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What single Ajv instance backs both middleware and direct payload validation, and what is the exact API-token extraction precedence?

## ajv validation funnel
**Path/Symbol:** `packages/nocodb/src/helpers/apiHelpers.ts` — whole file 102L: module-level ajv (:19–23), `getAjvValidatorMw` (:26–45), `validatePayload` (:48–71), `getApiTokenFromHeader` (:78–102).
**Signature:** `getAjvValidatorMw(schema: string) → express RequestHandler`; `validatePayload(schema: string, payload: any, humanReadableError = false, context?: {api_version?}) → void (throws)`; `getApiTokenFromHeader(req?) → string | undefined`.
**Data Shape:** one shared `Ajv({strictSchema:false, strict:false, allErrors:true})` + addFormats + ajvErrors; schemas registered as `'swagger.json'` and `'swagger-v3.json'`.

### Decisive source
```ts
// :26–44 — mw path returns 400 JSON; :55–70 — direct path throws:
export const getAjvValidatorMw = (schema: string) => {
  return (req, res, next) => {
    const validate = ajv.getSchema(schema);
    const valid = validate(req.body);
    if (valid) {
      next();
    } else {
      const errors: ErrorObject[] = ajv.errors || [];
      const formatted = formatAjvErrors(errors);
      res.status(400).json({
        message: formatAjvErrorMessage(errors),
        errors: formatted,
      });
    }
  };
};
// :88–101 — token precedence:
// 1) Prefer explicit xc-token header
const token = headers['xc-token'];
if (typeof token === 'string' && token.trim()) return token.trim();
// 2) Fallback to Authorization: Bearer ***
const value = auth.trim();
if (value.toLowerCase().startsWith('bearer ')) return value.slice(7).trim();
```

**Flow:** MW path answers 400 with `{message, errors}`; DIRECT path (`validatePayload`, used by services/websockets) throws via `NcError.ajvValidationError({message, errors, humanReadableError})` with a missing-schema guard that 404s (`genericNotFound('Validation schema', schema)`); allErrors:true collects every violation for the formatter. TOKEN extraction trims, case-insensitive `bearer ` prefix match, slices 7.
**Invariant:** The SAME compiled validators serve both paths — a schema name typo fails differently per surface (400 vs 404-throw). Bearer fallback accepts ANY credential-bearing Authorization header shape only when prefixed exactly `bearer ` (case-insensitive); non-Bearer schemes yield undefined so downstream auth strategies can own them.
**Probe:** `grep -c "xc-token" packages/nocodb/src/helpers/apiHelpers.ts` → `3`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "getAjvValidatorMw validatePayload getApiTokenFromHeader", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-Ajv sharing, dual error surfaces (400-json vs throw), and xc-token→Bearer precedence verbatim; adapt swagger registration names to host schema registry.
