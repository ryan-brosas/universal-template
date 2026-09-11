<!-- capsule-v2 -->
# Lazy datasource encryption backfill — how do you encrypt existing connection configs when an operator sets the key for the first time?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Which rows get encrypted, at what scope, and when does the whole pass roll back?

## is_encrypted=false sweep under one transaction
**Path/Symbol:** `packages/nocodb/src/helpers/initDataSourceEncryption.ts:initDataSourceEncryption` (whole 117L); called from `init-meta-service.provider.ts:171`.
**Signature:** `initDataSourceEncryption(_ncMeta = Noco.ncMeta): Promise<void>`; no-op unless NC_CONNECTION_ENCRYPT_KEY set.
**Data Shape:** targets = SOURCES (per base_id scope) + INTEGRATIONS (workspace scope via RootScopes.WORKSPACE,WORKSPACE) where is_encrypted IS false OR NULL AND config NOT NULL; payload {config: encrypted, is_encrypted: true}.

### Decisive source
```ts
const sources = await ncMeta
  .knex(MetaTable.SOURCES)
  .where((qb) => {
    qb.where('is_encrypted', false).orWhereNull('is_encrypted');
  })
  .whereNotNull('config');
...
// if all failed, throw error
if (successStatus.length && successStatus.every((status) => !status)) {
  throw new Error('Failed to encrypt all data sources, please remove invalid data sources and try again.');
}
```
(:22–:27, :104–:108)

**Flow:** per row: skip empty config; JSON.parse validity check FIRST — invalid JSON is logged and recorded as failure WITHOUT aborting siblings → encryptPropIfRequired wraps the whole source/integration record → metaUpdate flips is_encrypted=true → after both sweeps: commit; if EVERY attempted row failed, throw so the catch rolls back the ENTIRE transaction and rethrows.
**Invariant:** partial success commits (one bad legacy config must not block boot), but TOTAL failure rolls back everything — a mixed outcome is the intended steady state with the failures retried next boot. The two tables use DIFFERENT meta scopes: SOURCES update under their own workspace/base ids while INTEGRATIONS always write at RootScopes.WORKSPACE. Idempotency rides the is_encrypted flag (false-or-null predicate), making re-runs free.
**Probe:** `cd packages/nocodb && grep -c "is_encrypted" src/helpers/initDataSourceEncryption.ts` (=5: 2 predicates + payload + comments) and `grep -c "RootScopes.WORKSPACE" src/helpers/initDataSourceEncryption.ts` (=2 integrations scope args) and `grep -c "successStatus.every" src/helpers/initDataSourceEncryption.ts` (=1).
**Direct test:** none upstream — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "initDataSourceEncryption encryptPropIfRequired is_encrypted NC_CONNECTION_ENCRYPT_KEY", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt flag-driven idempotent backfill with per-row isolation + total-failure rollback + dual-scope writes; adapt to your KMS/secret envelope; omit if configs were never stored plaintext. Coverage caveat: grep-pinned only.
