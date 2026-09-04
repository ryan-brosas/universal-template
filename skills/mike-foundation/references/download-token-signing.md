<!-- capsule-v2 -->
# Download token signing — how do persistent file links survive without signed-URL expiry?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How does a backend issue download links that are safe to store permanently in chat history yet remain un-forgeable and storage-path-agnostic?

## HMAC over an encoded payload, verified BEFORE decoding
**Path/Symbol:** `backend/src/lib/downloadTokens.ts:42` (`signDownload`), `:52` (`verifyDownload`), `:37` (`timingSafeEqStr`), `:79` (`buildDownloadUrl`). Direct test: `backend/src/lib/__tests__/downloadTokens.test.ts`.
**Signature:** `signDownload(path, filename) -> "enc.sig"`; `verifyDownload(token) -> { path, filename } | null`.
**Data Shape:** payload JSON `{ p: storagePath, f: filename }` → base64url (no padding) → `enc.HMAC-SHA256(enc)` with both parts base64url. Secret from `DOWNLOAD_SIGNING_SECRET`, hard-thrown at first use if unset.

### Decisive source
```ts
const expected = crypto.createHmac("sha256", getSecret()).update(enc).digest();
// compare the ENCODE forms as strings — never decode-then-trust the payload first
if (!timingSafeEqStr(sigEnc, b64urlEncode(expected))) return null;
const parsed = JSON.parse(b64urlDecode(enc).toString("utf8")); // only after sig holds
```

**Flow:** sign at artifact-creation time → URL `/download/<token>` persisted in chat history/UI cards → route splits on "." requiring EXACTLY two parts → HMAC recomputed from `enc` alone → timing-safe compare → only then JSON.parse and require both `p` and `f`.
**Invariant:** Signature verification precedies any payload parsing; a tampered payload, tampered signature, 1-part or 3-part token, missing field, or wrong secret all return `null` (not throw). No expiry claim is encoded — persistence IS the feature; revocation means rotating the secret.
**Probe:** `grep -c 'it(' src/lib/__tests__/downloadTokens.test.ts` → 15 (`it(` incl. nested helpers; vitest reports **12 passed** at pin) (round-trip, tampered payload/sig, too many/few parts, missing fields, different secret); suite green via `bunx vitest run`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "signDownload verifyDownload HMAC download token", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sign-encode/verify-before-decode ordering + two-part shape + timing-safe encoded comparison + fail-null semantics; adapt secret management and URL prefix to your host; omit R2-specific CORS rationale (any object store works).
