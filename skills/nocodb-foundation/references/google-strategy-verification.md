<!-- capsule-v2 -->
# Google sign-in unverified-email gate — how is an attacker-controlled address blocked from matching a local account?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does Google sign-in reject unverified emails, and which flag shapes does it understand?

## Dual-shape verification flags with narrow fail-closed window
**Path/Symbol:** `packages/nocodb/src/strategies/google.strategy/googleEmailVerification.ts:isGoogleEmailUnverified` (whole file 29L) · call site `strategies/google.strategy/google.strategy.ts:GoogleStrategy.validate` (:40–:52).
**Signature:** `isGoogleEmailUnverified(profile: any, email: string): boolean`.
**Data Shape:** understands BOTH passport-profile shape (`emails[i].value`/`emails[i].verified`/`_json.email_verified`) and raw ID-token shape (`email_verified`); collects every available flag and returns true when ANY is present-and-false (boolean false OR string `"false"`).

### Decisive source
```ts
const emails = profile?.emails;
if (Array.isArray(emails)) {
  const match = emails.find((e) => e?.value === email) ?? emails[0];
  if (match && typeof match === 'object' && 'verified' in match) {
    flags.push((match as any).verified);
  }
}
const json = profile?._json ?? profile;
if (json && typeof json === 'object' && 'email_verified' in json) {
  flags.push((json as any).email_verified);
}
// Present-and-false (boolean false or the string "false") => unverified.
return flags.some((v) => v === false || v === 'false');
```
(:12–:27)

**Flow:** validate() takes `profile.emails[0].value` → calls the checker BEFORE any user lookup → unverified ⇒ emit `USER_SIGNIN_FAILED {reason: 'Email not verified by Google'}` + `done(new Error('Email not verified'))` → verified ⇒ proceed to find-or-provision local User by email and resolve role bags (existing user gets base roles overlaid when req.ncBaseId resolves).
**Invariant:** fails CLOSED only when a flag is PRESENT and false — absent flags are ALLOWED so providers that omit them keep working; narrowing further (reject-absent) locks out providers that never send the field, widening (trust-present) defeats the gate. The email match inside `emails[]` prefers exact-value match before falling back to first entry — keeps multi-email profiles honest about WHICH address is being signed in.
**Probe:** `cd packages/nocodb && grep -c "in match\|in json" src/strategies/google.strategy/googleEmailVerification.ts` (=2 presence guards) and `grep -n "isGoogleEmailUnverified(profile, email)" src/strategies/google.strategy/google.strategy.ts` (:40 single call site).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "isGoogleEmailUnverified email_verified USER_SIGNIN_FAILED GoogleStrategy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the collect-all-flags/present-and-false-rejects semantics and the pre-lookup gate position; adapt provider profile shapes; omit if SSO handled upstream. Coverage caveat: spec files construction-only stubs; probes count-pinned. ERRATUM vs first draft: no tokeninfo HTTP call exists in this tree — the gate reads profile flags only.
