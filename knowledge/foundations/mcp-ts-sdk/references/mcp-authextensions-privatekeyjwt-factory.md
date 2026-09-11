<!-- capsule-v2 -->
# createPrivateKeyJwtAuth — how does a `private_key_jwt` client assertion get minted per request, and which key forms map to which import?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What is the exact key-import ladder, claim set, and audience fallback order a porter must reproduce for RFC 7523 JWT-bearer client authentication?

## Assertion factory closure (AddClientAuthentication implementation)
**Path/Symbol:** `packages/client/src/client/authExtensions.ts` `createPrivateKeyJwtAuth` (:27-95).
**Signature:** `(options: { issuer: string; subject: string; privateKey: string | Uint8Array | Record<string, unknown>; alg: string; audience?: string | URL; lifetimeSeconds?: number; claims?: Record<string, unknown> }) => AddClientAuthentication` — returns `async (_headers, params, url, metadata) => void`.
**Data Shape:** Claims `{ iss, sub, aud, exp: now + lifetimeSeconds, iat: now, jti }`; `jti = \`${Date.now()}-${Math.random().toString(36).slice(2)}\`` (:50); default lifetime 300s; custom `options.claims` spread AFTER baseClaims so caller keys win (:60).

### Decisive source
```ts
const jose = await import('jose');

const audience = String(options.audience ?? metadata?.issuer ?? url);
```
(:44-46 — lazy `import('jose')` keeps the heavy dep out unless used; audience fallback ladder explicit-option → AS-metadata issuer → token-endpoint URL)

**Flow:** crypto-presence gate FIRST (`globalThis.crypto === undefined` → TypeError pointing at the README's Web Crypto section :38-42) → lazy jose import → resolve audience + lifetime → build claims with jti → import key by FORM LADDER: string + `alg` startsWith RS/ES/PS → `importPKCS8(pem, alg)`; string + HS → `TextEncoder().encode(privateKey)` (raw UTF-8 HMAC secret); Uint8Array + HS → use bytes as-is; Uint8Array non-HS → decode UTF-8 then `importPKCS8` (assumed PKCS#8 DER); object → `importJWK(key, alg)`; anything else → `throw new Error('Unsupported algorithm ' + alg)` (:65-79) → sign via `new jose.SignJWT(claims)` with protected header `{ alg, typ: 'JWT' }` (:82-90) → finally `params.set('client_assertion', …)` + `params.set('client_assertion_type', 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer')` (:92-93).
**Invariant:** The alg-prefix dispatch happens on the STRING prefix of the algorithm (`RS*`/`ES*`/`PS*` asymmetric vs `HS*` symmetric), not on key type — an HS256 alg with a PEM string takes the HMAC branch and fails at sign time, not import time. The assertion-type URN is fixed; only the assertion varies.
**Probe:** `grep -cF 'options.lifetimeSeconds ?? 300' packages/client/src/client/authExtensions.ts` → 1 (:47); `grep -cF '{ ...baseClaims, ...options.claims }' …` → 1 (:60); direct tests `packages/client/test/client/authExtensions.test.ts` describe `createPrivateKeyJwtAuth` :250 incl. `it('throws when globalThis.crypto is not available'…)` :275, Uint8Array-HMAC :297, metadata.issuer-audience :359, custom-claims :428.
**Caveat:** some tool output elides this file's long identifiers hygienically; derive every grep anchor byte-exactly (fixed-string form) before pinning.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", name_pattern: "createPrivateKeyJwtAuth|AssertionCallback", limit: 10 });
```
(BM25 query-mode scatters to wrong-plane conformance/example files for this seam; the name_pattern alternation resolves the factory itself.)

## Verdict
Adopt the whole ladder — key-form dispatch, claim merge precedence, audience fallback chain, and the two param names. Adapt key loading to host keystores as long as the PKCS#8/JWK/HMAC split stays. Omit nothing from the error paths: the crypto-gate TypeError text is load-bearing documentation for older Node users.
