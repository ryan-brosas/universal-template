<!-- capsule-v2 -->
# runInTransaction composition — how do 90 public methods share ONE transaction when callers already hold one?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What is the join-or-create transaction idiom used by every sub-manager, and why do some methods deliberately NOT use it?

## runInTransaction(transaction, op) joins an existing EntityManager or opens connection.transaction; _connection.transaction is reserved for method-rooted flows
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `runInTransaction` (:3570–3576), `RunInTransaction` type (`Interfaces.ts` :50–53), deliberate `_connection.transaction` roots: addWorkspace (:1573), updateOrg (:1445 uses runInTransaction), deleteUser fork phase (:584, outside any tx), notification loops (post-commit by construction).
**Signature:** `runInTransaction<T>(transaction: EntityManager | undefined, op: (manager) => Promise<T>): Promise<T>` — `if (transaction) { return op(transaction); } return this._connection.transaction(op);`.
**Data Shape:** Sub-managers receive the bound function at construction (`this.runInTransaction.bind(this)` :295–298), so every UsersManager/GroupsManager/ServiceAccountsManager method composes without importing the manager.

### Decisive source
```ts
/**
 * Run an operation in an existing transaction if available, otherwise create
 * a new transaction for it.
 */
public runInTransaction<T>(
  transaction: EntityManager | undefined,
  op: (manager: EntityManager) => Promise<T>,
): Promise<T> {
  if (transaction) { return op(transaction); }
  return this._connection.transaction(op);
}
```
Composition example — service-account creation reusing one tx across three managers' methods:
```ts
return await this._connection.transaction(async (manager) => {
  const owner = await this._homeDb.getUser(ownerId);
  ...
  const serviceUser = await this._homeDb.getUserByLogin(login, { manager }, "service");
  await this._homeDb.createApiKey(serviceUser.id, false, manager);
```

**Flow:** root operations open `_connection.transaction`; helpers called with `{manager}` or `optManager` JOIN it; repair/notification phases intentionally run after. The sqlite caveat from pass-7's TypeORMPatches capsule applies: sqlite serializes everything anyway, so join-vs-create matters mainly on postgres.
**Invariant:** Methods that MUST have their own atomic boundary (addWorkspace's limit-check-then-insert, deleteDocument's multi-table cascade) call `_connection.transaction` directly and accept a manager param only for their INTERNAL helpers. A porter who blindly converts those to runInTransaction lets callers compose limit checks with unrelated writes, breaking the fail-closed windows.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -c "runInTransaction" app/gen-server/lib/homedb/HomeDBManager.ts app/gen-server/lib/homedb/UsersManager.ts app/gen-server/lib/homedb/GroupsManager.ts'` → ≥ 20 combined.
`bash -c 'grep -c "_connection.transaction" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 15.
Direct tests: concurrency its (`HomeDBManager.ts` :53 parallel user creation) exercise nesting indirectly; SetupRequests concurrent RMW test pins outer behavior.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"runInTransaction RunInTransaction EntityManager transaction","limit":8,"detail":"ids"}'`

**Verdict:** ADAPT — small idiom but it is the skeleton every other homedb capsule sits on; port without it and the choreographies above deadlock or double-commit.
