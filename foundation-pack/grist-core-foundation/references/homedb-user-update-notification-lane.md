<!-- capsule-v2 -->
# updateUser isWelcomed side channel — how does a profile mutation trigger first-login automation without coupling persistence to notifications?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where does "user just finished onboarding" get detected, and how do notifications stay outside the transaction?

## UsersManager returns {previous, current, isWelcomed}; the facade converts isWelcomed into a notifier.firstLogin call AFTER the tx returns
**Path/Symbol:** `app/gen-server/lib/homedb/UsersManager.ts`: `updateUser` (:303–335, flag flip :322–329, structuredClone previous :313); `HomeDBManager.ts` wrapper (:495–504), `_notifier: INotifier = new EmitNotifier()` default (:316), notification-factory pattern (`_inviteNotification` :5313, `_teamCreatorNotification` :5327, `_streamingDestinationsChange` :5333).
**Signature:** `updateUser(userId, props: UserProfileChange) => Promise<PreviousAndCurrent<User>>` — public signature DROPS isWelcomed (consumed internally).
**Data Shape:** `UserProfileChange = {name?, isFirstTimeUser?, disabledAt?, options?}`; welcome fires only on `isFirstTimeUser: false` transition (`if (!props.isFirstTimeUser) { isWelcomed = true; }`).

### Decisive source
```ts
const previous = structuredClone(user);
...
if (props.isFirstTimeUser !== undefined && props.isFirstTimeUser !== user.isFirstTimeUser) {
  user.isFirstTimeUser = props.isFirstTimeUser;
  needsSave = true;
  // If we are turning off the isFirstTimeUser flag, then right
  // after this transaction commits is a great time to trigger
  // any automation for first logins
  if (!props.isFirstTimeUser) { isWelcomed = true; }
}
if (needsSave) { await manager.save(user); }
return { previous, current: user, isWelcomed };
```
```ts
// HomeDBManager.updateUser
const { previous, current, isWelcomed } = await this._usersManager.updateUser(userId, props);
if (current && isWelcomed) {
  await this._notifier.firstLogin(this.makeFullUser(current));
}
```

**Flow:** every mutation method in the file follows the SAME shape: collect `notifications: (() => Promise<void>)[]` inside the transaction → run them in a loop AFTER `this._connection.transaction(...)` resolves. The notifier itself is injectable (constructor param, default no-op-ish EmitNotifier) so tests and alternate deployments swap delivery.
**Invariant:** Notifications fire even when the caller ignores the result — they are awaited by whoever called the manager, INSIDE the request but OUTSIDE the DB transaction: a failed email fails the API call AFTER data committed. A porter who awaits side effects inside the tx risks rollback-on-email-bounce; one who fires-and-forgets loses retry semantics. The isWelcomed bit is deliberately NOT in the public PreviousAndCurrent type — automation is an implementation detail of the facade.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -c "for (const notification of notifications)" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 6.
`bash -c 'grep -n "firstLogin" app/gen-server/lib/Notifier.ts | head -2'` → interface + implementations.
Direct tests: `test/gen-server/lib/emails.ts` (notification assertions incl. first-login mail), ApiServerAccess notificationConfig-gated asserts (:591).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"updateUser isFirstTimeUser _notifier firstLogin INotifier notifications","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — the boolean-out-of-persistence + post-commit-notification-loop idiom is reusable far beyond Grist.
