<!-- capsule-v2 -->
# WWW-Authenticate challenge builder — how do you emit a spec-correct Bearer challenge that hostile error text cannot break?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** The `WWW-Authenticate` value embeds verifier-authored error strings — what exact quoting/sanitization keeps the header RFC 7235-valid and the Response constructor throw-free?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/middleware/bearerAuth.ts`: `headerQuotedValue` (:57-63) + `buildWwwAuthenticateHeader` (:65-79), consumed by `bearerAuthChallengeResponse` (:136-163). Graph qn `typescript-sdk.packages.server.src.server.middleware.bearerAuth.bearerAuthChallengeResponse`.
**Signature:** `headerQuotedValue(value: string): string` (private); `buildWwwAuthenticateHeader(errorCode: string, description: string, requiredScopes: string[], resourceMetadataUrl: string|undefined): string` (private).
**Data Shape:** Output = `Bearer error="…", error_description="…"[, scope="a b c"][, resource_metadata="url"]` — auth-param quoted-strings per RFC 7235, fixed field order.

### Decisive source
```ts
function headerQuotedValue(value: string): string {
    // HTTP quoted-string per RFC 7235: escape backslash and double quote, and
    // replace characters a header cannot carry (controls, anything beyond
    // printable ASCII) so a verifier-authored message can never make the
    // challenge Response constructor throw.
    return value.replaceAll(/[\\"]/g, String.raw`\$&`).replaceAll(/[^\u0020-\u007E]/g, ' ');
}
let header = `Bearer error="${headerQuotedValue(errorCode)}", error_description="${headerQuotedValue(description)}"`;
if (requiredScopes.length > 0) { header += `, scope="${requiredScopes.join(' ')}"`; }
if (resourceMetadataUrl) { header += `, resource_metadata="${resourceMetadataUrl}"`; }
```

**Flow:** sanitize each interpolated value (escape `\`+`"` FIRST via `$&`, then blank every char outside printable ASCII) → assemble in pinned order error → error_description → scope (space-joined, only when non-empty) → resource_metadata (only when configured). Scope values are NOT sanitized — they are operator-configured constants, not attacker/verifier text; only dynamic strings pass through `headerQuotedValue`.

**Invariant:** Sanitization is a PRE-EMISSION gate on all verifier-controlled text: without it, `'bad "token"\r\nnext'` would either throw inside `new Response(…, {headers})` or smuggle a second header line. Escaping order matters — backslash/quote escaping must run BEFORE the non-printable blanking so the escape backslash itself survives. Challenge presence is semantic: emitted ONLY for invalid_token/insufficient_scope (never server_error/400) so clients never interpret a server fault as an auth requirement.

**Probe:** `packages/server/test/server/bearerAuth.test.ts` — :98 full-field regex pinning field ORDER (`error`, `error_description`, `scope`, `resource_metadata` last), :110 scope in 403 challenge, :170 non-ASCII message ⇒ `'token invalide  '` (é+… blanked to spaces, still 401), :176 quote-escape + CR/LF strip (`error_description="bad \"token\"  next"`), :182 hostile-message gate resolves as Response not rejection, :119/:125 challenge ABSENT for server_error/other codes.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "WWW-Authenticate bearerAuthChallengeResponse headerQuotedValue", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt sanitize-then-assemble with this exact regex pair and field order for any header embedding dynamic text. Adapt which fields your challenge carries. Omit per-value sanitization of operator-static fields like scope.
