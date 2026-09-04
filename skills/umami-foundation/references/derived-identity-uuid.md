<!-- capsule-v2 -->
# Derived session & visit identity — how do you compute a stable anonymous session id without cookies?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are session and visit ids derived so they're stable per device but rotate on time windows, without storing client state?

## derived-identity-uuid
**Path/Symbol:** `src/lib/crypto.ts:uuid/getSalt/secret/hash` (:48-78); `src/app/api/send/route.ts:154-193`.
**Signature:** `uuid(...parts) = uuidv5(sha512(parts.join('') + secret()), v5.DNS)`; `getSalt(rotation, date) = sha512(startOf<day|week|month>(date).toUTCString())`.
**Data Shape:** sessionId = `uuid(sourceId, ip, userAgent, sessionSalt)`; visitId = `uuid(sessionId, visitSalt)` where `visitSalt = hash(startOfHour(createdAt).toUTCString())`. No ids stored client-side.

### Decisive source
```ts
const sessionSalt = getSalt(saltRotation, createdAt);      // SALT_ROTATION: day|week|month (default month)
const visitSalt = hash(startOfHour(createdAt).toUTCString());
const sessionId = uuid(sourceId, ip, userAgent, sessionSalt);
const sessionDrift = !!websiteId && !!cache?.sessionId && cache.sessionId !== sessionId;
...
let visitId = cache?.visitId || uuid(sessionId, visitSalt);
let iat = cache?.iat || now;
if (!timestamp && now - iat > 1800) {                      // 30-minute visit window
  visitId = uuid(sessionId, visitSalt);
  iat = now;
}
```

**Flow:** same (sourceId, ip, UA) inside one salt period → identical sessionId; visits bucket by hour-salt AND expire after 30 idle minutes (`now - iat > 1800`), whichever fires first.
**Invariant:** salt rotation is the privacy knob — rotating salts changes ALL historical session ids at the boundary (a session "splits" at each period edge; that is intended). The `sessionDrift` branch forces a FRESH visitId + iat when the recomputed session no longer matches the cached one — never reuse the old visit with a new session.
**Probe:** `grep -n "creates separate sessions" src/lib/session.test.ts` → :13 (with :7 same-device stability) — exercises exactly this derivation via `uuid()`.
**Probe:** `grep -n "1800" src/app/api/send/route.ts` → :191.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "getSalt uuid sessionSalt visitSalt drift", limit: 10 });
```

## Verdict
Adopt hash-derived identity + dual time-window rotation for cookieless analytics or rate-limit keying; adapt rotation periods and the 30-min window to product needs; omit DNS-namespace v5 quirk if your UUID lib offers a custom namespace.
