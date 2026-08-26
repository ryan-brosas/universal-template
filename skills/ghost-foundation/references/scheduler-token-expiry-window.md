<!-- capsule-v2 -->
# Scheduler JWT expiry window — how long is a scheduler publish URL valid?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What exp/not-before window must a signed schedule URL carry so late publishes and network retries both work?

## getSignedAdminToken
**Path/Symbol:** `ghost/core/core/server/adapters/scheduling/utils.ts:getSignedAdminToken` (:11–40).
**Signature:** `({ publishedAt: string, apiUrl: string, key: InternalApiKey }): string`.
**Data Shape:** `key = {id, secret}` where secret is HEX-encoded bytes; HS256; `audience = apiUrl`; `noTimestamp: true` (no iat — expiry is anchored to published_at, not signing time).
### Decisive source
```ts
const opts: SignOptions = { keyid: key.id, algorithm: 'HS256', audience: apiUrl, noTimestamp: true };
let tokenExpiry = moment(publishedAt).add(6, 'h');
if (tokenExpiry.isBefore(moment())) {
  tokenExpiry = moment().add(6, 'h');
}
return jwt.sign(
  { exp: tokenExpiry.unix(), nbf: moment(publishedAt).subtract(10, 'm').unix() },
  Buffer.from(key.secret, 'hex'),
  opts,
);
```
**Flow:** exp = published_at + 6h (floored to now + 6h when publishing in the past) → nbf = published_at − 10min → sign with hex-decoded secret.
**Invariant:** `noTimestamp:true` + published_at-anchored claims mean re-issuing the token for the SAME published_at yields an identical token — this is what makes same-key reschedule URLs stable across boot rebuilds. The 10-min nbf slack lets a slightly-early scheduler ping succeed; the past-floor keeps retries alive after downtime. Secret MUST be hex-decoded to raw bytes before HMAC or verification fails against stored byte secrets.
**Probe:** `grep -cF "noTimestamp: true" ghost/core/core/server/adapters/scheduling/utils.ts` → expect `1`; `grep -cF "add(6, 'h')" ghost/core/core/server/adapters/scheduling/utils.ts` → expect `2` (assignment + floor branch); `grep -cF "subtract(10, 'm')" ghost/core/core/server/adapters/scheduling/utils.ts` → expect `1`; `grep -cF "Buffer.from(key.secret, 'hex')" ghost/core/core/server/adapters/scheduling/utils.ts` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "getSignedAdminToken", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the published_at-anchored exp/nbf window with no iat. Adapt key storage format; keep the hex-decode step if secrets are stored hex-encoded.
