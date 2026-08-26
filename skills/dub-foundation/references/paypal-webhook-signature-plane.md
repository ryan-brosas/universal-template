<!-- capsule-v2 -->
# PayPal webhook signature verification — cert-host allowlist, Redis-cert cache, and the CRC32 message contract

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How is a PayPal webhook proven authentic without trusting the caller-supplied certificate URL?

## verifySignature + isValidPayPalCertUrl + downloadAndCache
**Path/Symbol:** `apps/web/app/(ee)/api/paypal/webhook/verify-signature.ts:verifySignature` (:62-101); guards `isValidPayPalCertUrl` (:17-28), `downloadAndCache` (:30-60); env `apps/web/lib/paypal/env.ts:paypalEnv` (:3-13).
**Signature:** `verifySignature({event: string /* RAW body */, headers: Headers}): Promise<boolean>`.
**Data Shape:** four paypal-* headers (transmission-id/sig/time/cert-url); sig = base64 SHA256withRSA over `<transmissionId>|<timeStamp>|<PAYPAL_WEBHOOK_ID>|<crc32-decimal>`; cert cached in Redis 7 days under sha256(url).

### Decisive source
```ts
if (!isValidPayPalCertUrl(certUrl)) {
  console.error(`[PayPal] Rejected non-PayPal certificate URL: ${certUrl}`);
  return false;
}

const certPem = await downloadAndCache(certUrl);
```
(verify-signature.ts :81-86)

and

```ts
const PAYPAL_CERT_HOST_ALLOWLIST = new Set([
  "api.paypal.com",
  "api-m.paypal.com",
  "api.sandbox.paypal.com",
  "api-m.sandbox.paypal.com",
]);

function isValidPayPalCertUrl(url: string): boolean {
  try {
    const parsed = new URL(url);

    return (
      parsed.protocol === "https:" &&
      PAYPAL_CERT_HOST_ALLOWLIST.has(parsed.hostname)
    );
  } catch {
    return false;
  }
}
```
(:10-28)

**Flow:** all four headers present? (missing ⇒ false, not throw) → cert URL parses AND https AND hostname in the four-host allowlist → fetch cert PEM with Redis cache-aside (`paypal:cert:<sha256(url)>`, TTL 7d, write via waitUntil so response never blocks on cache set) → compute crc32 of the RAW body string → `parseInt("0x"+hex)` to decimal → verify base64 signature against the pipe-joined message with crypto.createVerify("SHA256") using the DOWNLOADED cert as trust anchor.
**Invariant:** the allowlist is the SSRF/trust boundary — an attacker-controlled certUrl would otherwise make verification validate against THEIR key; the webhook id enters the signed message (not compared separately), which is why PAYPAL_WEBHOOK_ID is consumed exactly here; verification runs on the raw pre-parse body because JSON re-serialization would change bytes and break crc32.
**Probe:** deterministic probes (repo root): `grep -n 'PAYPAL_CERT_HOST_ALLOWLIST' "apps/web/app/(ee)/api/paypal/webhook/verify-signature.ts"` → :10/:23; `grep -c 'sandbox.paypal.com' "apps/web/app/(ee)/api/paypal/webhook/verify-signature.ts"` → 2; `grep -n 'paypal-transmission-id' "apps/web/app/(ee)/api/paypal/webhook/verify-signature.ts"` → :69; `grep -n 'CERT_CACHE_TTL_SECONDS' ...` → :8/:53; `grep -n 'crc32(event)' ...` → :93; `grep -rn 'PAYPAL_WEBHOOK_ID' apps/web/lib apps/web/app --include='*.ts'` resolves ONLY env.ts + this file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "verifySignature", limit: 5, fields: ["signature", "name", "file"] });
```
(also live: `isValidPayPalCertUrl` :17-28, `downloadAndCache` :30-60 — route by file.)

## Verdict
Adopt the host allowlist + https gate, cache-aside cert fetch, and exact message grammar. Adapt crypto/Redis transports. Omit nothing.
