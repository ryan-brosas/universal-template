<!-- capsule-v2 -->
# getUserByLogin upsert + email-key race retry — how does "fetch user by email, creating if unseen" survive concurrent first logins?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where does SSO profile data get written back into the user record, and how is the create-race handled?

## One method lazily migrates profile fields onto the User/Login rows with a needUpdate flag; one retry absorbs postgres unique-key races
**Path/Symbol:** `app/gen-server/lib/homedb/UsersManager.ts`: `getUserByLogin` (:432–553), `getUserByLoginWithRetry` (:366–378), `getExistingUserByLogin`/`getExistingUsersByLogin` (:383–404, non-creating twins), `initializeSpecialIds` (:644–661) + `_maybeCreateSpecialUserId` (:994–1005).
**Signature:** `getUserByLogin(email: string, options: GetUserOptions = {}, type: UserType = "login")`; options = `{manager?, profile?, userOptions?}`.
**Data Shape:** Query joins user+logins+personalOrg filtered on NORMALIZED email. Field-by-field fill ladder: name (deduce from email local-part via `_getNameOrDeduceFromEmail` :1007), picture, displayEmail from provider, connectId, authSubject link-in, ssoExtraInfo merge, firstLoginAt (only when a profile is present!), lastConnectionAt (day-granular).

### Decisive source
```ts
// Fetch user from login, creating the user if previously unseen, allowing one retry
// for an email key conflict failure. This is in case our transaction conflicts with a peer
// doing the same thing. This is quite likely if the first page visited by a previously
// unseen user fires off multiple api calls.
public async getUserByLoginWithRetry(email: string, options: GetUserOptions = {}): Promise<User> {
  try {
    return await this.getUserByLogin(email, options);
  } catch (e) {
    if (e.name === "QueryFailedError" && e.detail?.match(/Key \(email\)=[^ ]+ already exists/)) {
      // This is a postgres-specific error message. This problem cannot arise in sqlite,
      // because we have to serialize sqlite transactions in any case...
      return await this.getUserByLogin(email, options);
    }
    throw e;
  }
}
```
Day-granular connection stamp:
```ts
const nowish = new Date();
nowish.setMilliseconds(0);
if (!user.lastConnectionAt || getTimestampStartOfDay(user.lastConnectionAt) !== getTimestampStartOfDay(nowish)) {
  user.lastConnectionAt = nowish;
```

**Flow:** after save, personal-org creation (`getPersonalOrgsEnabled() && !user.personalOrg && !NON_LOGIN_EMAILS.includes(...)`) rides addOrg with PERSONAL_FREE_PLAN + showGristTour pref; then `user = await userQuery.getOne()` RELOAD for consistent relations (:546–550). NON_LOGIN_EMAILS = previewer/everyone/anonymous → those users never get isFirstTimeUser=true, so no welcome redirect. Special-user bootstrap uses the same WithRetry path because "there'll be a race to create the user if a bunch of servers start simultaneously" (:997–999).
**Invariant:** firstLoginAt only stamps when `profile` was supplied — API-key-only traffic doesn't count as first login. The retry matches a POSTGRES error-string shape (`e.detail` Key (email)=...); sqlite's serialized transactions make it moot there — porters on other ORMs must map THEIR duplicate-key error shape, not copy the regex blindly.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -c "NON_LOGIN_EMAILS" app/gen-server/lib/homedb/UsersManager.ts'` → ≥ 3.
`bash -c 'grep -n "parallel requests resulting in user creation give consistent results" test/gen-server/lib/HomeDBManager.ts'` → :53.
Direct tests: `test/gen-server/lib/HomeDBManager.ts` :53 (100 concurrent creations all deep-equal), :38 ("can find existing user by email"), :68 ("can accumulate profile information"); `test/gen-server/lib/homedb/UsersManager.ts` :564 ("should normalize email address").

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"getUserByLoginWithRetry ensureExternalUser _maybeCreateSpecialUserId initializeSpecialIds","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — canonical lazy-provisioning upsert; the retry-once-on-dup-email contract is the part every reimplementation needs.
