<!-- capsule-v2 -->
# API-key lifecycle — how are machine tokens created, rotated and revoked at the user plane?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What does the minimal safe api-key column lifecycle look like?

## crypto.randomBytes hex token stored on User.apiKey; create is create-or-409 unless force; lookup joins logins for downstream auth convenience
**Path/Symbol:** `app/gen-server/lib/homedb/UsersManager.ts`: `apiKeyGenerator` (:37–39), `createApiKey` (:963–976), `deleteApiKey` (:978–987), `getApiKey` (:954–961), `getUserByKey` (:168–171).
**Signature:** `createApiKey(userId: number, force: boolean, transaction?: EntityManager): Promise<User>` — existing key without force → 400 "An apikey is already set, use `{force: true}` to override it."
**Data Shape:** Token = `crypto.randomBytes(20).toString("hex")` (40 chars, no prefix); storage = plain column on users; null means no key. `getApiKey` maps null → "" for display ("The null value is of no interest to the user").

### Decisive source
```ts
function apiKeyGenerator(): string {
  return crypto.randomBytes(20).toString("hex");
}
...
if (!user.apiKey || force) {
  user.apiKey = apiKeyGenerator();
  return await manager.save(User, user);
} else {
  throw new ApiError("An apikey is already set, use `{force: true}` to override it.", 400);
}
```
Lookup side:
```ts
public async getUserByKey(apiKey: string): Promise<User | undefined> {
  // Include logins relation for Authorization convenience.
  return await User.findOne({ where: { apiKey }, relations: ["logins"] }) || undefined;
}
```

**Flow:** create/rotate/delete each open their own transaction when none supplied (`_runInTransaction(transaction, ...)`) so they compose inside larger flows (ServiceAccountsManager calls createApiKey mid-create with its manager :58). Deletion sets null rather than deleting the row. Auth middleware resolves users by key via getUserByKey and never sees the write path.
**Invariant:** Rotation requires EXPLICIT force — a client that re-POSTs without force cannot accidentally invalidate a live credential; service-account key rotation passes force:true deliberately (:191). No hashing of keys at rest (keys ARE secrets shown once to the user) — porters adding hashing must change lookup to keyed-hash comparison, not reuse findOne.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "randomBytes(20)" app/gen-server/lib/homedb/UsersManager.ts'` → :38.
`bash -c 'grep -rn "apiKey" test/gen-server/ApiServer.ts | head -3'` → endpoint coverage.
Direct tests: `test/gen-server/ApiServer.ts` api-key its (create/dup/force/delete round trip).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"createApiKey deleteApiKey getUserByKey apiKeyGenerator","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT as the minimal baseline; pair with access-tokens-rolling-doc-secrets.md for doc-scoped rotating secrets.
