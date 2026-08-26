<!-- capsule-v2 -->
# Credential JWE keyring — how do stored secrets survive key rotation and row-swap attacks?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** What is the minimal correct envelope for encrypting provider API keys in your own database?

## Compact JWE, dir + A256GCM, kid + context AAD
**Path/Symbol:** `packages/lib/src/secrets/crypto.ts:keyId` (L50–52), `encryptSecret` (L54–61), `decryptSecret` (L74–96), `getKeyring` (L111–134); overlay `secrets/store.ts:getCredential` (L21–23), `refreshCredentialOverlay` (L39–71).
**Signature:** `encryptSecret(plaintext, {key, aad}): Promise<EncryptedPayload>`; `decryptSecret(payload, {keyring, aad}): Promise<string>`; `getKeyring(env): Keyring | null`.
**Data Shape:** protected header carries `{alg:"dir", enc:"A256GCM", kid, ctx:aad}` where `kid = sha256("elmo-secret-key-id\0" + key).hex[:16]` (domain-separated so it can't double as a plain hash elsewhere) and `ctx = "secret:" + envVarName`. Keyring = `{primary, byId: Map<kid,key>}` built from `ELMO_ENCRYPTION_KEY` plus comma-separated retired `ELMO_ENCRYPTION_KEY_OLD`.

### Decisive source
```ts
// Both halves are needed. Editing `ctx` breaks the tag — but jose
// authenticates the header the payload carries, not the one the caller
// expected. Comparing them is what stops a whole ciphertext being moved onto
// another credential's row by someone with DB write access.
if (protectedHeader.ctx !== opts.aad) throw new Error("payload context mismatch");
```
And the rotation-completeness gate:
```ts
// Silently ignoring this would leave a half-finished rotation looking complete
if (retired.length > 0 && no current key) throw new EncryptionKeyError(`${RETIRED_KEYS_ENV} is set without ${ENCRYPTION_KEY_ENV}`);
```

**Flow:** reads choose the key by `kid` from the untrusted header — safe because the header is AEAD additional data, so rewriting it fails the tag. Overlay rebuild decrypts every secrets row into a fresh Map, skipping (not throwing) unknown-name or undecryptable rows with per-row diagnostics ("restore that key there to finish the rotation" for UnknownKeyError vs "may be corrupt or tampered with" otherwise), then swaps atomically — a failed load leaves the old overlay serving.
**Invariant:** name-bound AAD + explicit ctx comparison = ciphertexts cannot be replayed under a different credential row even by an attacker with DB write. UnknownKeyError is DISTINCT from SecretDecryptError because the remedies differ (restore key vs re-enter secret).
**Probe:** `packages/lib/src/secrets/crypto.test.ts` + `store.test.ts` (58 tests GREEN in this probe run: round-trips, wrong-key/ctx tampering, retirement-without-primary throw, overlay skip-and-swap).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "encryptSecret decryptSecret getKeyring refreshCredentialOverlay UnknownKeyError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whole — this is a textbook-minimal secret store; adapt the env-var names and AAD format; omit the overlay interval-refresh if you read credentials only from env.
