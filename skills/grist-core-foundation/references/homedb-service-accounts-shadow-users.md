<!-- capsule-v2 -->
# Service accounts as shadow users — how do API-only machine identities ride the same user/login tables without ever logging in?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where does a service account actually live, and what invariants keep it un-loginable?

## ServiceAccount = owner-linked row + synthetic User of type "service" whose login is `<uuid>@serviceaccounts.invalid` + forced apiKey
**Path/Symbol:** `app/gen-server/lib/homedb/ServiceAccountsManager.ts`: `createServiceAccount` (:38–70), `_buildServiceAccountQuery` (:238–244), ownership assert `_assertExistingAndOwned` (:223–230), key lifecycle (:184–217); `app/gen-server/entity/Login.ts`: `SERVICE_ACCOUNTS_TLD = "serviceaccounts.invalid"` (:17) + type-consistency check (:41–42).
**Signature:** `createServiceAccount(ownerId: number, props?: ServiceAccountProperties): Promise<ServiceAccount>`; every mutator takes `options: { expectedOwnerId?, transaction? }`.
**Data Shape:** Login email = `${uuidv4()}@${SERVICE_ACCOUNTS_TLD}` — RFC 2606 `.invalid` TLD means no email can ever be delivered, so no email-link login path exists. Owner must be `type === "login"` (403 otherwise). Deletion sets `serviceUser.disabledAt = new Date()` BEFORE removing the account row.

### Decisive source
```ts
// We use .invalid as tld following RFC 2606
// as we don't ever want service user to be able to receive any email
// and then be able to connect via link in email
const login = `${uuid}@${Login.SERVICE_ACCOUNTS_TLD}`;
// Using getUserByLogin will create the user... Yeah, please don't blame us.
const serviceUser = await this._homeDb.getUserByLogin(login, { manager }, "service");
await this._homeDb.createApiKey(serviceUser.id, false, manager);
```
Ownership guard used by every mutating endpoint:
```ts
private _assertExistingAndOwned(serviceAccount: ServiceAccount | null, expectedOwnerId: number | undefined):
  asserts serviceAccount is ServiceAccount {
  this._assertExisting(serviceAccount);
  if (expectedOwnerId !== undefined && serviceAccount.ownerId !== expectedOwnerId) {
    throw new ApiError("Cannot access non-owned service account", 403);
  }
}
```

**Flow:** create → shadow user via the standard upsert (type "service") → apiKey minted immediately → ServiceAccount row links owner+serviceUser. Reads join serviceUser+logins (+owner when requested). Key rotation calls `createApiKey(id, true /*force*/)`; deletion disables the user rather than deleting (audit trail preserved).
**Invariant:** The Login entity VALIDATES that type-"service" users carry the `.invalid` TLD (:41–42) — two layers enforcing non-loginability. Ownership checks are opt-in per call (`expectedOwnerId`) but every public wrapper passes it; a porter who forgets one creates an IDOR on machine credentials. `testDeleteAllServiceAccounts` exists ONLY for tests ("outside of tests context will lead to partial db destruction").

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "serviceaccounts.invalid" app/gen-server/entity/Login.ts'` → :17.
`bash -c 'grep -n "Only regular users" app/gen-server/lib/homedb/ServiceAccountsManager.ts'` → :48.
Direct tests: `test/gen-server/ApiServer.ts` service-account its (grep `serviceAccount`); Login entity validation exercised via migrations/user suites.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"ServiceAccountsManager SERVICE_ACCOUNTS_TLD createServiceAccount createApiKey","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — machine-identity-via-shadow-user is the pattern; the `.invalid` TLD trick is the detail that makes it safe.
