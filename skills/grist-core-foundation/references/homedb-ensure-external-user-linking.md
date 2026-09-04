<!-- capsule-v2 -->
# ensureExternalUser connectId sync — how does a second SSO provider claim or update an existing identity without creating duplicates?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What happens when the same person logs in via a NEW external provider (different email) — new user, or linked existing?

## Lookup by connectId first; found → field-diff sync of login/name/picture; not found → full getUserByLogin creation with isFirstTimeUser suppressed
**Path/Symbol:** `app/gen-server/lib/homedb/UsersManager.ts`: `ensureExternalUser` (:254–301), connectId branch (:257–270), diff-sync block (:272–299).
**Signature:** `ensureExternalUser(profile: UserProfile)` — profile carries `{email, name, picture, connectId?}`.
**Data Shape:** Update path splices the Login in place (`existing.logins.splice(0, 1, login)` — handles users whose login row is MISSING by constructing a fresh one); saves `[existing, login]` only when something changed (`updated` flag).

### Decisive source
```ts
const existing = await manager.findOne(User, {
  where: { connectId: profile.connectId || undefined },
  relations: ["logins"],
});
// If a user does not exist, create it with data from the external profile.
if (!existing) {
  const newUser = await this.getUserByLoginWithRetry(profile.email, { profile, manager });
  // No need to survey this user.
  newUser.isFirstTimeUser = false;
  await manager.save(newUser);
} else {
  // Else update profile and login information from external profile.
  let updated = false;
  let login: Login = existing.logins[0];
  const properEmail = normalizeEmail(profile.email);
  if (properEmail !== existing.loginEmail) {
    login = login ?? new Login();
    login.email = properEmail;
    login.displayEmail = profile.email;
    ...
```

**Flow:** external-provider flows call this before session work; created users skip onboarding survey (isFirstTimeUser=false) because their identity came pre-verified. Email change on an existing connectId user rewrites BOTH login.email (normalized, unique key) and displayEmail.
**Invariant:** `connectId || undefined` matters — TypeORM would otherwise query `connect_id = NULL` matching every unlinked row. Changing login.email here is a LIVE UNIQUE-KEY RENAME inside a transaction; a collision throws QueryFailedError uncaught (deliberate loud failure). A porter who upserts by email instead of connectId splits one human into two accounts across providers.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "should normalize email address" test/gen-server/lib/homedb/UsersManager.ts'` → :564.
`bash -c 'grep -c "connectId" app/gen-server/lib/homedb/UsersManager.ts'` → ≥ 4.
Direct tests: `test/gen-server/lib/homedb/UsersManager.ts` ensureExternalUser family (:526 no-op, :535 save unknown, :543 update existing, :564 normalization).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"ensureExternalUser connectId UserProfile isFirstTimeUser","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — multi-provider identity linking with minimal-surprise field sync; the connectId-first lookup order is the whole point.
