<!-- capsule-v2 -->
# Encrypted OAuth credential store — how do you keep third-party tokens at rest so a DB leak does not hand out working tokens?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How are provider OAuth tokens stored, re-used on reconnect, and loaded back into a typed shape — and what breaks if any step is lenient?

## Versioned AES-GCM envelope + composite-key upsert + fail-loud load
**Path/Symbol:** `apps/web/src/features/credentials/mutations.ts:saveOAuthCredentials` (lines 9–55); `apps/web/src/features/credentials/data.ts:loadCredential` (lines 24–51); cipher `packages/utils/src/encryption.ts:encrypt`/`decrypt` (lines 17–99); schema `features/credentials/schema.ts:oauthCredentialsSchema`.
**Signature:** `saveOAuthCredentials({ userId, provider, providerAccountId, tokens }) → Credential`; `loadCredential(credentialId) → CredentialsInfo | null`.
**Data Shape:** one `credential` row per `(userId, provider, providerAccountId)` composite unique; `secret` is a single base64 string = `version(1B) ‖ salt(32B) ‖ iv(12B) ‖ authTag(16B) ‖ ciphertext`; key derived per call via PBKDF2-SHA256 @ 210,000 iterations from `env.SECRET_PASSWORD`. Load output is `{ id, type:"oauth", provider, secret: {accessToken, refreshToken?, expiresAt?, scopes[]}, scopes, expiresAt }` or null.

### Decisive source
```ts
// mutations.ts — re-connecting the same account UPDATEs, never accumulates
const credential = await prisma.credential.findUnique({
  where: { user_provider_account_unique: { userId, provider, providerAccountId } },
});
if (credential) {
  return await prisma.credential.update({ where: { id: credential.id },
    data: { secret: encrypt(JSON.stringify(tokens), env.SECRET_PASSWORD), scopes: tokens.scopes, expiresAt: tokens.expiresAt } });
}
return await prisma.credential.create({ data: { type: "OAUTH", ..., secret: encrypt(...) } });
```
```ts
// data.ts — decrypt → JSON.parse → zod parse: fail-loud on shape drift
secret: oauthCredentialsSchema.parse(JSON.parse(decrypt(credential.secret, env.SECRET_PASSWORD))),
```
```ts
// encryption.ts — the envelope header is what makes migration possible
const version = Buffer.from([CURRENT_VERSION]);            // 1-byte prefix
const combined = Buffer.concat([version, salt, iv, authTag, ciphertext]);
// decrypt: if (version !== CURRENT_VERSION) throw new Error(`Unsupported encryption version: ${version}`);
```

**Flow:** OAuth callback (state-verified, see oauth-pkce-cookie-state-machine) → `saveOAuthCredentials` upserts by composite key with fresh encrypted tokens → later, `syncCalendars` calls `loadCredential(connection.credentialId)` → decrypt → JSON.parse → zod parse → hand the plain object to the provider service constructor, which validates it AGAIN with its own `credentialsSchema` (defense in depth at the use site).
**Invariant:** the ciphertext column is useless without `SECRET_PASSWORD` — AES-256-GCM with a fresh random salt+IV per call (non-deterministic, so equal tokens produce different blobs and row-diffing leaks nothing), and GCM's auth tag makes truncation/tampering fatal at decrypt time. The 1-byte version byte is the only forward-compatibility seam: a future algorithm bump throws a named error instead of mis-decrypting. The read path is deliberately NOT lenient (contrast the notification-prefs codec): a credential that fails zod means the token shape changed under you, and silently defaulting would produce a half-working API client — throwing surfaces it.
**Probe:** direct test `packages/utils/src/encryption.test.ts` (roundtrip incl. unicode/multiline, wrong-password failure at :101, invalid-base64 throw at :133, non-determinism at :15). No test for credentials/data.ts|mutations.ts themselves (caveat). Behavioral anchors verified by direct read: composite unique at mutations.ts:22–25, encrypt calls at :34/:48, decrypt→parse chain at data.ts:42–44, PBKDF2 iterations at encryption.ts:9, version gate at :63.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "saveOAuthCredentials loadCredential", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the version-prefixed salt‖iv‖tag‖ciphertext base64 envelope for any password-derived field encryption — the version byte is the difference between a migration and a data-loss incident. Adopt composite-key upsert semantics for per-account secrets (re-auth refreshes in place). Adapt the key source: Rallly derives from one shared `SECRET_PASSWORD`, which couples credential decryption to every other secret in the instance; if you can, give credentials their own key. Omit the double validation only if your provider client already rejects bad shapes loudly. Caveat: no direct tests on the feature layer; the cipher itself is well-tested.
