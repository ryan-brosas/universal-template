<!-- capsule-v2 -->
# transformInstallConfig seed-and-lock RMW — how do you make a whole-JSON-value read-modify-write concurrency-safe on two backends?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What does an atomic config update look like when the value is ONE json column and sqlite has no row locks?

## lock row if it exists; else orIgnore()-seed then re-lock under the winner's row; transform + save — all in one transaction
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `transformInstallConfig` (:3181–3206), `updateInstallConfig` (:3159–3170, 201-vs-200 envelope), `getOrgConfig`/`updateOrgConfig`/`deleteOrgConfig` (:3244–3349), `_installConfig`/`_orgConfig` builders (:3679–3710), `lockForUpdate` (`app/gen-server/sqlUtils.ts` :144–157).
**Signature:** `transformInstallConfig(key: ConfigKey, seed: ConfigValue, transform: (value) => ConfigValue): Promise<{created: boolean; previous: Config | null; current: Config}>`.
**Data Shape:** `configs = {key, value: jsonb/json, org_id nullable}` — org_id NULL means install-scope. `lockForUpdate(dbType, qb)`: postgres → `.setLock("pessimistic_write")`; sqlite → identity (transactions globally serialized via TypeORMPatches); other → THROW (never silently unlocked).

### Decisive source
```ts
// Concurrency-safe — a config holds one whole JSON value, so a plain read-modify-write
// could drop a concurrent writer's change. An existing row is taken under lockForUpdate;
// the first writer (no row to lock) seeds one with orIgnore() and re-reads under the lock.
return this._connection.transaction(async (manager) => {
  const lock = () => lockForUpdate(this._dbType, this._installConfig(key, { manager })).getOne();
  let current = await lock();
  const created = !current;
  const previous = current ? structuredClone(current) : null;
  if (!current) {
    // No row to lock yet: seed one. orIgnore() turns a concurrent creator's race into a
    // no-op; re-reading under the lock yields the winning row.
    await manager.createQueryBuilder().insert().into(Config)
      .values({ key, value: seed }).orIgnore().execute();
    current = (await lock())!;
  }
  current.value = transform(current.value);
  await manager.save(current);
  return { created, previous, current };
});
```

**Flow:** REST layer wraps for whole-value replace (201 create vs 200 previous+current) and signals streaming-destination listeners post-commit (`_streamingDestinationsChange`). Org-scoped variants gate on Permissions.OWNER and reuse the same previous/current clone discipline.
**Invariant:** The double-lock dance exists because a missing row cannot be locked: seeding with orIgnore() makes exactly one creator win and the loser's re-lock reads the WINNER's row. A porter who skips the re-read applies transform to their own seed and clobbers the winner. structuredClone BEFORE transform is what fills `previous`. Postgres bigint COUNTs need CAST(... AS INTEGER) elsewhere in this file — same backend-duality discipline.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "does not lose concurrent requests" test/server/lib/SetupRequests.ts'` → :122.
`bash -c 'grep -c "orIgnore" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 3.
Direct tests: `test/server/lib/SetupRequests.ts` :122–133 hammers transformInstallConfig with 20 concurrent single-requester merges asserting all 20 survive ("with a naive read-modify-write most of these would overwrite each other").

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"transformInstallConfig lockForUpdate orIgnore installConfig ConfigKey","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — smallest complete recipe in the file for portable pessimistic RMW over dual backends.
