<!-- capsule-v2 -->
# WWW-Authenticate challenge parsing — how does a client read resource_metadata/scope/error out of a 401 challenge without a full header parser?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** What exactly is extracted from a `WWW-Authenticate: Bearer …` header, and which malformed inputs are silently dropped vs rejected?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/auth.ts`: `extractWWWAuthenticateParams` (:1456-1493), private `extractFieldFromWwwAuth` (:1502-1520); consumers (graph trace, 13 call sites): both transports' `_send`/`send`/`resumeStream`, `handleOAuthUnauthorized`, `onUnauthorized`, `middleware.withOAuth`, conformance `withOAuthRetry.handle401`. GRAPH LINE DRIFT: search_graph reported :1418-1455; source of record is :1456-1493.
**Signature:** `extractWWWAuthenticateParams(res: Response): { resourceMetadataUrl?: URL; scope?: string; error?: string; errorDescription?: string }`
**Data Shape:** single header value; fields appear as `name="quoted"` or `name=unquoted`; unknown fields (`realm`) ignored.

### Decisive source
```ts
// :1467-1470 — scheme gate on the FIRST space-split token only
const [type, scheme] = authenticateHeader.split(' ');
if (type?.toLowerCase() !== 'bearer' || !scheme) {
    return {};
}
// :1508 — quoted-or-unquoted field regex; first match wins
const pattern = new RegExp(String.raw`${fieldName}=(?:"([^"]+)"|([^\s,]+))`);
// :1475-1481 — invalid resource_metadata URL is DROPPED silently
try { resourceMetadataUrl = new URL(resourceMetadataMatch); } catch { /* Ignore invalid URL */ }
```

**Flow:** 401 response → header absent ⇒ `{}` → not bearer-typed ⇒ `{}` → per-field regex reads
(`resource_metadata`, `scope`, `error`, `error_description`) → `resource_metadata` parsed as URL,
invalid values become `undefined` while sibling fields still surface.

**Invariant:** case-insensitive scheme match but NO challenge-parameter grammar beyond
quoted/unquoted — no escape handling, no comma-split across multiple challenges (the first match
in the raw string wins); a non-bearer challenge (`Basic realm=…`) yields `{}` even when it carries
scope/resource_metadata. Empty-string field values normalize to `undefined`
(`extractFieldFromWwwAuth(...) || undefined`). Porters needing multi-challenge or RFC 9110
strict parsing must extend, not copy.

**Probe:** `packages/client/test/client/auth.test.ts` :87-194 — bearer-only extraction
(:110-122 Basic ⇒ `{}`), invalid URL dropped but scope kept (:134-146), `invalid_token` +
`error_description` full tuple (:158-175), scope+error+description triple (:177-193).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "typescript-sdk", function_name: "extractWWWAuthenticateParams", direction: "both" });
```

## Verdict
Adopt as the pragmatic single-challenge reader feeding discovery + step-up; adapt the field list to
your challenge vocabulary; omit if you already own an RFC 9110/6750 challenge parser — this one
trades strictness for zero dependencies. Companion: www-authenticate-challenge-builder.md owns the
SERVER-side builder; bearer-token-gate.md owns the server verify ladder.
