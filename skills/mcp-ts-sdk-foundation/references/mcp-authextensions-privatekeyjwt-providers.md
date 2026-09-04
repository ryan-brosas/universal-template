<!-- capsule-v2 -->
# PrivateKeyJwtProvider + StaticPrivateKeyJwtProvider — when must the assertion be minted fresh vs pinned at construction?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What distinguishes the signing provider from the static-assertion provider, and what does each stamp into clientInfo/metadata that a porter must keep identical?

## Twin providers over one factory (fresh-mint vs pre-built assertion)
**Path/Symbol:** `packages/client/src/client/authExtensions.ts` `PrivateKeyJwtProvider` (:285-354) and `StaticPrivateKeyJwtProvider` (:397-464).
**Signature:** both `implements OAuthClientProvider` with public field `addClientAuthentication: AddClientAuthentication`; options interfaces are the `…Options` siblings (:216-263 / :359-388).
**Data Shape:** Signing variant: `{ clientId, privateKey, algorithm, clientName?, jwtLifetimeSeconds?, scope?, claims?, expectedIssuer? }`. Static variant: `{ clientId, jwtBearerAssertion, clientName?, scope?, expectedIssuer? }` — a pre-built JWT string used verbatim.

### Decisive source
```ts
this.addClientAuthentication = createPrivateKeyJwtAuth({
    issuer: options.clientId,
    subject: options.clientId,
    privateKey: options.privateKey,
    alg: options.algorithm,
    lifetimeSeconds: options.jwtLifetimeSeconds,
    claims: options.claims
});
```
(:303-310 — issuer AND subject both default to clientId; RFC 7523 §3 allows sub=client_id for M2M)

vs the static twin (:416-420):
```ts
const assertion = options.jwtBearerAssertion;
this.addClientAuthentication = async (_headers, params) => {
    params.set('client_assertion', assertion);
    params.set('client_assertion_type', 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer');
};
```

**Flow:** Signing variant delegates to `createPrivateKeyJwtAuth` so every token request mints a FRESH exp/jti assertion (never replay-stale). Static variant closes over one assertion — appropriate only where the IdP accepts long-lived assertions or an external process rotates the string; no expiry is enforced client-side. Both stamp `_clientInfo.issuer = expectedIssuer` (SEP-2352) and declare `token_endpoint_auth_method: 'private_key_jwt'`, `grant_types: ['client_credentials']`.
**Invariant:** The two classes share EVERY provider member except the `addClientAuthentication` body — porters who fork the skeleton instead of parameterizing it will drift the throwing-member asymmetry (silent `saveCodeVerifier` vs throwing `codeVerifier`). The static form performs NO time-validity check: if your host needs rotation, that logic lives outside this class by design.
**Probe:** `grep -cF 'export class PrivateKeyJwtProvider ' packages/client/src/client/authExtensions.ts` → 1 (:285); `grep -cF 'export class StaticPrivateKeyJwtProvider ' …` → 1 (:397); `grep -oF 'PrivateKeyJwtProviderOptions' … | wc -l` → 4; direct tests :83/:126/:158 (signing), :179/:216 (static), custom-claims pass-through :451.
**Caveat:** identifiers in this file render elided in some tool output (`PrivateK***`) — never copy prose; anchor on byte-level fixed strings.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "prepareTokenRequest client_credentials provider", limit: 10, fields: ["signature", "name", "file"] });
```
(resolves all three prepareTokenRequest twins rank#1-3)

## Verdict
Adopt the twin split: fresh-mint per request as default, static closure only for externally-managed assertions. Adapt the metadata defaults (`client_name` fallbacks like `'private-key-jwt-client'`) to host naming. Omit nothing — the shared-skeleton-plus-one-field design IS the reusable contract.
