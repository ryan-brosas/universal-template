<!-- capsule-v2 -->
# Identity token minting — how are members handed short-lived RS256 tokens for cross-subdomain auth?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What claims and key type does the member identity token carry, and how does it differ from admin API keys?

## IdentityTokenService
**Path/Symbol:** `ghost/core/core/server/services/identity-tokens/identity-token-service.ts:IdentityTokenService` (:3–32).
**Signature:** `constructor(privateKey, issuer, keyId)`; `async getTokenForUser(email: string, role?: string): Promise<string>`.
**Data Shape:** claims `{sub: email, role?}`; RS256 PRIVATE-key signing (asymmetric — verifiers need only the public half); `expiresIn: '5m'`; `keyid` header set.
### Decisive source
```ts
const token = sign(claims, this.privateKey, {
  issuer: this.issuer,
  expiresIn: '5m',
  algorithm: 'RS256',
  keyid: this.keyId,
});
```
**Flow:** site requests an identity token for a member email → sign sub=email (+optional role) with the site's RSA private key → member client presents it to another Ghost service/subdomain which verifies against the public key (looked up by kid) within 5 minutes.
**Invariant:** Contrast with the two HS256 planes: admin API keys are symmetric per-integration secrets verified server-side only (kid→DB lookup), while identity tokens are asymmetric so THIRD parties can verify without a shared secret. The subject is the EMAIL not a user id, because consumers may not share a database. 5-minute TTL matches the admin JWT maxAge default — both are "short bearer window" tokens.
**Probe:** `grep -cF "algorithm: 'RS256'" ghost/core/core/server/services/identity-tokens/identity-token-service.ts` → expect `1`; `grep -cF "expiresIn: '5m'" ghost/core/core/server/services/identity-tokens/identity-token-service.ts` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "IdentityTokenService getTokenForUser", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-token taxonomy (admin HS256 keyed, scheduler URL HS256 no-maxAge, member identity RS256). Adapt claim vocabulary; keep email-as-sub only if consumers accept it.
