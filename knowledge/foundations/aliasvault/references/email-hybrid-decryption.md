<!-- capsule-v2 -->
# Email hybrid decryption with non-extractable key cache — how are server-side encrypted mails opened client-side without leaking RSA keys?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What is the per-email envelope format, and why is the private-key cache keyed by PUBLIC key?

## Hybrid envelope
**Path/Symbol:** `apps/browser-extension/src/utils/EncryptionUtility.ts:340-383` (`decryptEmail`), :321-335 (`getPrivateKeyObject` + cache), :431-458 (`decryptAttachment`).
**Signature:** `decryptEmail(email: Email, encryptionKeys: EncryptionKey[]): Promise<Email>`; cache type `Map<string /*PublicKey JWK*/, Promise<CryptoKey>>`.
**Data Shape:** Each email carries `encryptionKey` (the matching public key) + `encryptedSymmetricKey` (RSA-OAEP-SHA256 base64); body fields (`subject`, `fromDisplay`, `fromDomain`, `fromLocal`, `messageHtml`, `messagePlain`, `messageSource`) are each independently AES-256-GCM base64 = `IV(12B) || ciphertext`; attachments decrypt as raw bytes via `symmetricDecryptBytes`.

### Decisive source
```ts
const cachedPrivateKey = EncryptionUtility.rsaPrivateKeyCache.get(encryptionKey.PublicKey);
if (cachedPrivateKey) { return await cachedPrivateKey; }
const privateKey = EncryptionUtility.importPrivateKey(encryptionKey.PrivateKey).catch(error => {
  EncryptionUtility.rsaPrivateKeyCache.delete(encryptionKey.PublicKey);
  throw error;
});
EncryptionUtility.rsaPrivateKeyCache.set(encryptionKey.PublicKey, privateKey);
```
```ts
// importPrivateKey — non-extractable by construction
return await crypto.subtle.importKey("jwk", JSON.parse(privateKey),
    { name: "RSA-OAEP", hash: "SHA-256" }, false, ["decrypt"]);
```

**Flow:** match `keys.find(key => key.PublicKey === email.encryptionKey)` (3 call sites) → cache-or-import private key → RSA-decrypt the symmetric key ONCE per email → AES-GCM-decrypt every field with the SAME symmetric key → return a shallow-cloned object (original never mutated) → list variant parallelizes with `Promise.all`.
**Invariants:** (1) Cache stores the PROMISE, not the key — concurrent decryptions share one import and a failed import evicts itself so retries aren't poisoned. (2) Keys imported non-extractable (`extractable=false`) close the JS-string leak surface the legacy path had (upstream spec pins this: "exposes private fields in JS string (leak surface the non-extractable variant closes)"). (3) `clearRsaPrivateKeyCache()` must run on vault lock/reset. (4) IV is always the FIRST 12 bytes of each field blob (`slice(0, 12)` ×2 sites).
**Probe:** `grep -c 'rsaPrivateKeyCache.delete' apps/browser-extension/src/utils/EncryptionUtility.ts` → `1`; `grep -c 'key.PublicKey === email.encryptionKey' apps/browser-extension/src/utils/EncryptionUtility.ts` → `3`; `grep -c 'slice(0, 12)' apps/browser-extension/src/utils/EncryptionUtility.ts` → `2`.

## Direct tests
**Path/Symbol:** `apps/browser-extension/src/utils/__tests__/EncryptionUtility.crypto.test.ts:110-300` — non-extractability ("rejects every attempt to export the private key" :119), cache-by-public-key (:169), gzip source (:237+).
**Probe:** run jest where node_modules exists; deterministic probes above executed at pin `95903e92`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "decryptEmail", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt promise-cached non-extractable RSA keys keyed by public key + per-field AES-GCM envelopes; adapt storage of key material; omit the legacy extractable path. Upstream crypto tests exist but were not executed here.
