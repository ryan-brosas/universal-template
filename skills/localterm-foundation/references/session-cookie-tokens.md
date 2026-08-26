<!-- capsule-v2 -->
# HMAC session cookies without a JWT library — stateless re-auth across tabs and WS upgrades

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you keep users logged in after a passkey/OIDC ceremony with ~40 lines and no token library?

## base64url(payload).base64url(HMAC) with strict re-validation and a 0o600 persisted secret
**Path/Symbol:** `packages/server/src/identity/session-cookie.ts` — `signSessionToken` (:43–50), `verifySessionToken` (:52–71), `loadOrCreateAuthSecret` (:28–41), `setSessionCookie`/`clearSessionCookie`/`readSessionIdentity` (:93–111), `isSecureRequest` (:78–83).
**Data Shape:** payload `{ sub: string, exp: number }` epoch-ms; token `base64url(json).` + `HMAC-SHA256(secret, data)` both base64url; cookie `localterm-auth`, max-age 7d, HttpOnly, SameSite=Lax, Path=/, Secure only on https surfaces; secret = 32 random bytes, base64url.

### Decisive source
```ts
export const verifySessionToken = (secret: string, token: string): string | null => {
  const dot = token.lastIndexOf(".");
  if (dot <= 0) return null;
  const data = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  const expected = sign(secret, data);
  const sigBytes = Buffer.from(sig);
  const expectedBytes = Buffer.from(expected);
  if (sigBytes.length !== expectedBytes.length || !timingSafeEqual(sigBytes, expectedBytes)) {
    return null;
  }
  try {
    const payload = JSON.parse(Buffer.from(data, "base64url").toString("utf8")) as SessionPayload;
    if (typeof payload?.sub !== "string" || typeof payload?.exp !== "number") return null;
    if (payload.exp < Date.now()) return null;
    return payload.sub;
  } catch {
    return null;
  }
};
```

**Flow:** login verify succeeds → `signSessionToken(secret, user)` set as cookie → every later tab/WS call `readSessionIdentity(context, secret)` → sub or null. First daemon boot mints the secret once: `loadOrCreateAuthSecret` writes `.tmp` mode 0o600 then renames — reads of an empty/corrupt file regenerate rather than reuse.
**Invariant:** signature compare is length-checked THEN constant-time; the payload is re-validated field-by-field after decode (a validly-signed but malformed payload still fails); expiry is checked at read time so revocation = delete the secret file, which invalidates EVERY session deliberately ("never silently reuse a weak/absent key"). `Secure` is derived from the browser's own Origin header first, then request URL, then x-forwarded-proto — and deliberately OMITTED on plain loopback HTTP so the cookie works on every local surface.
**Probe:** `packages/server/tests/session-cookie.test.ts` (8 its) — round-trip verifies :18–20, wrong secret rejected :22–24, tampered suffix rejected :26–30, malformed shapes rejected :32–36, Set-Cookie carries HttpOnly + round-trips through real Hono headers :42–61, no-cookie → null :63–72, secret persists and reloads identical :81–92. Executed this pass, green.
**Retrieve (executed live):**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "signSessionToken|verifySessionToken|loadOrCreateAuthSecret|setSessionCookie|readSessionIdentity", limit: 10 });
```

## Verdict
Adopt this instead of pulling jose/jwt when all you need is "who, until when": HMAC over a two-field JSON payload, timing-safe compare, strict post-decode validation, tmp+rename 0o600 secret. Adapt max-age and secure-detection to your surfaces; omit claims/audience machinery unless you have multiple consumers. Traps: trusting the decoded JSON without re-validating shape; making Secure unconditional (breaks loopback HTTP) or never (breaks https); storing the secret in a world-readable file.
