<!-- capsule-v2 -->
# Signup claim race guard — how do you serialize account creation across the bcrypt gap without a real lock?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Between "email not taken" and "insert user" sits a slow hash — what stops two concurrent signups from both winning?

## Short-TTL claim key wrapping ONLY the create branch
**Path/Symbol:** `packages/nocodb/src/helpers/signupClaim.ts:withSignupClaim` (:26–58); consumer: `src/services/users/users.service.ts` signup path.
**Signature:** `withSignupClaim<T>(email: string, findExisting: () => Promise<unknown>, create: () => Promise<T>): Promise<T>`.
**Data Shape:** claim key `signup_claim:<normalizedEmail>`; CLAIM_TTL_SECONDS = 10.

### Decisive source
```ts
// Only has to outlive the re-check + insert below (a few ms). Kept short because
// it is a crash net: if a process dies mid-insert, that one address cannot
// register until the key expires.
const claimed = await NocoCache.setIfNotExist('root', key, '1', CLAIM_TTL_SECONDS);
if (!claimed) {
  NcError.badRequest('User already exist');
}
try {
  if (await findExisting()) {
    NcError.badRequest('User already exist');
  }
  return await create();
} finally {
  // Swallowed: awaiting bare, a Redis blip here would replace an already-created
  // account with a 500, and the retry would hit "User already exist". The TTL
  // releases the claim anyway.
  await NocoCache.del('root', key).catch(() => {});
}
```
(:5–:8, :33–:57)

**Flow:** atomic SETNX claims the canonical email (10s TTL) → loser gets 'User already exist' IMMEDIATELY (it may be mid-insert) → winner re-checks existence then creates → finally deletes the claim with errors swallowed (TTL is the real releaser).
**Invariant:** wrap ONLY the create branch — the invite path UPDATES an existing row and must reject concurrent acceptance differently, so callers keep invites outside. Best-effort semantics are explicit: setIfNotExist returns true unconditionally when cache is disabled (single-process deployments rely on the DB unique constraint as backstop). The claim's whole job is to bridge find-existing→insert, so its lifetime is seconds, not minutes.
**Probe:** `cd packages/nocodb && grep -c "CLAIM_TTL_SECONDS" src/helpers/signupClaim.ts` (=2: decl + use) and `grep -c "User already exist" src/helpers/signupClaim.ts` (=2 rejects + comment = counted by substring as 4 total incl comments) and `grep -c "setIfNotExist" src/helpers/signupClaim.ts` (=2: comment + call).
**Direct test:** none upstream for helpers/signupClaim.ts — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "withSignupClaim CLAIM_TTL setIfNotExist signup", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt claim-key serialization of just the create branch + swallow-the-release; adapt TTL to your insert latency budget; omit if your DB unique index plus retry UX suffices. Coverage caveat: grep-pinned only.
