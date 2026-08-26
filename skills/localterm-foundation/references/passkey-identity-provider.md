<!-- capsule-v2 -->
# Passkey identity provider — become your own WebAuthn identity authority with file-backed users

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How does a daemon issue its own logins (no external IdP) using WebAuthn, with durable users but zero password storage?

## Kind-tagged single-use challenges + two tiny zod JSON stores
**Path/Symbol:** `packages/server/src/identity/passkey-provider.ts` — `ChallengeStore` (:42–61), `resolveRp` (:92–105), `buildPasskeyRoutes` (:126–256), `createPasskeyIdentityProvider` (:264–291); `user-store.ts:UserStore` (:23–89); `credential-store.ts:CredentialStore` (:34–94).
**Data Shape:** ChallengeStore: `Map<challenge, { kind: "register"|"login", expiresAt }>`, TTL 5 min (`AUTH_CHALLENGE_TTL_MS`). UserStore (~state dir/users.json): username → credentialIds. CredentialStore (credentials.json): credentialId → { publicKey base64 COSE, counter, username }. Both versioned zod schemas, atomic tmp+rename writes, fail-open empty on corrupt.

### Decisive source
```ts
// Single-use: delete on read, return true only if it matched the expected
// kind and hadn't expired. A register challenge can't satisfy a login verify
// (and vice versa), and a consumed challenge can't be replayed.
consume(challenge: string, kind: "register" | "login"): boolean {
    const entry = this.challenges.get(challenge);
    this.challenges.delete(challenge);
    return entry?.kind === kind && entry.expiresAt >= Date.now();
  }
```
Wired as `expectedChallenge: (challenge) => deps.challenges.consume(challenge, "register")` inside simplewebauthn's verify — the library asks, the store answers consume-once.

**Flow:** register/options (403 when registration "closed") → normalizeUsername (1..256 trimmed) → resolveRp from the browser's Origin header (fallback daemon announced origin; null → 400 invalid_origin) → generateRegistrationOptions with excludeCredentials from the user's existing ids → challenge stored as kind "register" → verify consumes the challenge, requires user verification, persists credential + user, sets the session cookie. Login/options works with or without username (discoverable credentials when absent); login/verify looks up by assertion id (unknown → 400), verifies with expectedOrigin/RPID, then updates the stored counter (cloned-authenticator detection). Challenges sweep lazily on each set and are lost on restart — fine for a 5-minute lifetime.
**Invariant:** RP ID is the Origin HOSTNAME, so a passkey is bound to the surface the user registered on — loopback and tailnet origins are different credentials by WebAuthn design; the code surfaces that instead of hiding it. In-memory challenges are single-use AND kind-tagged AND TTL-bounded: replay, cross-flow confusion, and stale options all fail closed.
**Probe:** `packages/server/tests/passkey.test.ts` (14 its) — UserStore findOrCreate/addCredential + reload persistence :26–37; CredentialStore put/get/updateCounter + reload :49–59; denyUnauthenticated true vs header false :78–83; register options scoped to request origin (rp.id = node.ts.net) :85–100; 400 no username :102–111; 400 malformed response :113–122; me null pre-login :124–129; discoverable login options :131–143; closed registration 403 :145–157. Executed this pass, green.
**Retrieve (executed live):**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "ChallengeStore|CredentialStore|UserStore|createPasskeyIdentityProvider|resolveRp|normalizeUsername", limit: 12 });
```

## Verdict
Adopt: in-memory kind-tagged challenge store consumed inside expectedChallenge, file-backed user/credential registries with strict zod + tmp+rename, origin-derived RPID. Adapt state-directory layout and registration policy to your host; omit residentKey/userVerification tuning unless your authenticator fleet demands it. Traps: reusing one challenge store for register and login; persisting challenges (restart-stale replays); deriving RPID from config instead of the browser's actual origin.
