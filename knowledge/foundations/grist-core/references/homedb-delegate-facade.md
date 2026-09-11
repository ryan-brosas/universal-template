<!-- capsule-v2 -->
# HomeDB delegate facade — how do you expose a 7.6kL persistence subsystem through one class without leaking TypeORM everywhere?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where does the home-server API surface end and the raw ORM begin, so a porter wires callers to the right layer?

## Manager holds three sub-managers by composition and re-exposes ~90 delegating one-liners
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `class HomeDBManager implements HomeDBAuth` (:293), sub-manager fields (:295–299), `usersManager()` (:322), delegation examples `updateUser` (:495–504), `createGroup` (:544–546). Sub-managers: `app/gen-server/lib/homedb/UsersManager.ts` (:56, header comment :51–55), `GroupsManager.ts` (:24), `ServiceAccountsManager.ts` (:11).
**Signature:** `_usersManager = new UsersManager(this, this.runInTransaction.bind(this))`; `_groupsManager = new GroupsManager(this._usersManager, ...)`; `_serviceAccountsManager = new ServiceAccountsManager(this, ...)`.
**Data Shape:** Each sub-manager takes `(homeDb, runInTransaction)` — they reach the connection only through `_homeDb.connection`, never own a DataSource. `Interfaces.ts` narrows the facade for consumers: `HomeDBAuth` (:118–129, login-plane subset) and `HomeDBDocAuth` (:133–136, `getDocAuthCached` subset); the comment admits "in practice we still just pass around the full HomeDBManager".

### Decisive source
```ts
export class HomeDBManager implements HomeDBAuth {
  public caches: HomeDBCaches | null;
  private _usersManager = new UsersManager(this, this.runInTransaction.bind(this));
  private _groupsManager = new GroupsManager(this._usersManager, this.runInTransaction.bind(this));
  private _serviceAccountsManager = new ServiceAccountsManager(
    this, this.runInTransaction.bind(this),
  );
```
And the wrapper that adds behavior on top of pure delegation (`HomeDBManager.updateUser`):
```ts
const { previous, current, isWelcomed } = await this._usersManager.updateUser(userId, props);
if (current && isWelcomed) {
  await this._notifier.firstLogin(this.makeFullUser(current));
}
return { previous, current };
```

**Flow:** ApiServer/billing code → HomeDBManager public method → sub-manager (owns the actual TypeORM calls) → connection. Sub-manager methods marked "not exposed by HomeDBManager" (`UsersManager.verifyAndLookupDeltaEmails` :733, `translateDeltaEmailsToUserIds` :830) are internal-only; HomeDBManager reaches them via `_usersManager.` directly (:2098, :2151, :2325).
**Invariant:** Porting rule — business logic lives in sub-managers; cross-cutting concerns (notifications, caching, notifier wiring) attach ONLY in the facade wrappers. UsersManager's class docstring is contractual: instance/static methods must be reached "through HomeDBManager", never imported standalone.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -c "this._usersManager\." app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 20 (delegation density).
`bash -c 'grep -n "It.s only meant to be used by HomeDBManager" app/gen-server/lib/homedb/UsersManager.ts app/gen-server/lib/homedb/GroupsManager.ts'` → both files.
Direct tests: `test/gen-server/lib/homedb/HomeDBManager.ts` (499L suite drives everything through the facade).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"HomeDBManager UsersManager GroupsManager ServiceAccountsManager delegate","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — any port of Grist's account/org model needs the same three-way split plus facade, or notifications and cache invalidation scatter across call sites.
