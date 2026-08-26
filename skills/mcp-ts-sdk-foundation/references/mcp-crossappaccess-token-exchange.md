<!-- capsule-v2 -->
# requestJwtAuthorizationGrant — which RFC 8693 params are mandatory, and what makes an IdP response a valid ID-JAG?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What exact form-urlencoded body and response schema does the ID-Token→ID-JAG exchange implement, and where does it refuse to run?

## Layer-2 token exchange (RFC 8693 request + IdJagTokenExchangeResponseSchema verdict)
**Path/Symbol:** `packages/client/src/client/crossAppAccess.ts` `requestJwtAuthorizationGrant` (:124-181); schema at `packages/core/src/auth.ts` `IdJagTokenExchangeResponseSchema` :153-161 (re-exported through `packages/core-internal/src/shared/auth.ts` one-to-one shims — new schemas belong in core, never in the shim).
**Signature:** `(options: { tokenEndpoint: string | URL; audience: string | URL; resource: string | URL; idToken: string; clientId: string; clientSecret?: string; scope?: string; fetchFn?: FetchLike }) => Promise<JwtAuthGrantResult>` where result = `{ jwtAuthGrant: access_token, expiresIn?, scope? }`.
**Data Shape:** Request body keys: `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`, `requested_token_type=urn:ietf:params:oauth:token-type:id-jag`, `audience`, `resource`, `subject_token=<idToken>`, `subject_token_type=urn:ietf:params:oauth:token-type:id_token`, `client_id`; OPTIONAL `client_secret` and `scope`.

### Decisive source
```ts
// Only include client_secret when provided — sending an empty/undefined secret
// triggers `invalid_client` on strict IdPs that registered this as a public client.
if (clientSecret) {
    params.set('client_secret', clientSecret);
}
```
(crossAppAccess.ts:140-144)

```ts
export const IdJagTokenExchangeResponseSchema = z
    .object({
        issued_token_type: z.literal('urn:ietf:params:oauth:token-type:id-jag'),
        access_token: z.string(),
        token_type: z.string().optional(),
        expires_in: z.number().optional(),
        scope: z.string().optional()
    })
    .strip();
```
(packages/core/src/auth.ts:153-161)

**Flow:** `assertSecureTokenEndpoint(tokenEndpoint)` FIRST (SEP-2207 TLS-or-loopback refusal before any credential leaves) → POST form-urlencoded → non-ok → parse body as OAuth error (`OAuthErrorResponseSchema.safeParse`) for a `Token exchange failed: <error> - <description>` throw, else raw-status fallback → ok → strict-parse with the schema → map to result. Schema semantics: `issued_token_type` is a REQUIRED literal — a JAG response claiming another type fails loudly; `token_type` is deliberately OPTIONAL because per RFC 8693 §2.2.1 it is informational for non-access tokens and RFC 6749 §5.1 makes it case-insensitive ("strict checking rejects conformant IdPs" — in-source comment).
**Invariant:** The public-client branch is ABSENCE of the param, not an empty value — sending `client_secret=''` breaks strict IdPs. The schema's only required members are `issued_token_type` + `access_token`; everything else is optional or stripped.
**Probe:** `grep -oF 'urn:ietf:params:oauth:token-type:id-jag' packages/client/src/client/crossAppAccess.ts | wc -l` → 1; `grep -cF 'issued_token_type: z.literal' packages/core/src/auth.ts` → 1; direct tests describe `requestJwtAuthorizationGrant` incl. `it('rejects a non-https token endpoint before sending credentials (SEP-2207)'…)` :9, loopback-permit :25, omits-secret-public-client :120, wrong issued_token_type :145, token_type-not-N_A-accepted :168.
**Caveat:** none — anchors byte-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "token exchange id-jag issued_token_type subject_token", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exact key set, the omit-don't-empty secret rule, and the two-required-field schema. Adapt error-message wording to host conventions but keep both failure shapes (OAuth-typed vs raw). Omit nothing from the TLS gate — it runs before credentials exist.
