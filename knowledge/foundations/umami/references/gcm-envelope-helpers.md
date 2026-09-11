<!-- capsule-v2 -->
# AES-256-GCM envelope helpers — what is the exact wire format for the two crypto envelopes (generic value + JWT-wrapping secure token)?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are encrypt/decrypt and createSecureToken/parseSecureToken framed, and why does parse return null instead of throwing?

## gcm-envelope-helpers
**Path/Symbol:** `src/lib/crypto.ts:encrypt/decrypt :16-45, secret :52-54`; `src/lib/jwt.ts:createSecureToken/parseSecureToken :16-26`.
**Signature:** generic: base64(`salt[64] || iv[16] || tag[16] || ciphertext`), key = PBKDF2-SHA-512(secret, salt, 10k, 32B); secure token = encrypt(jwt.sign(payload)).
**Data Shape:** every payload carries a FRESH random salt+IV per encryption; auth-tag appended by position not length-prefix.

### Decisive source
```ts
const KEY_POSITIONS: SALT_LENGTH=64; IV_LENGTH=16; TAG_LENGTH=16; TAG_POSITION=SALT_LENGTH+IV_LENGTH; ENC_POSITION=TAG_POSITION+TAG_LENGTH;
// decrypt slices by CONSTANT offsets — format is positional, versionless
const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
decipher.setAuthTag(tag);
return decipher.update(encrypted) + decipher.final('utf8');   // GCM throws on tamper
...
export function parseSecureToken(token, secret) {
  try { return jwt.verify(decrypt(token, secret), secret); }
  catch { return null; }                                       // ALL failures ⇒ null
}
```

**Flow:** sign JWT → AES-GCM encrypt the STRING → store/transmit base64 → decrypt (auth failure throws) → verify JWT → payload or null. Auth middleware treats null as anonymous.
**Invariant:** double verification (GCM integrity + JWT signature) means tampering fails at EITHER layer; the catch-null contract is what lets route code do `payload || {}` instead of try/catch everywhere. Per-message salts make identical payloads produce different ciphertexts.
**Probe:** structural pins: `grep -n "ENC_POSITION" src/lib/crypto.ts | head -2` → :11,:40; `grep -c "return null" src/lib/jwt.ts` → 2.
**Probe:** `grep -n "pbkdf2Sync" src/lib/crypto.ts` → :13.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "encrypt decrypt createSecureToken parseSecureToken", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt positional GCM envelope + null-returning verify wrappers as app-crypto baseline; adapt KDF iterations upward (10k is dated); never reuse these helpers for data-at-rest requiring key rotation metadata.
