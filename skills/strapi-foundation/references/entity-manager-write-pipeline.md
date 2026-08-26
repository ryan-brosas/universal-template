<!-- capsule-v2 -->
# Entity-manager write pipeline — how do you keep main-row and link-table writes consistent when they cannot share one transaction?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** What is the exact ordering of lifecycle dispatch, defaults, row write, relation write, rollback, and re-read that makes create/update/delete safe?

## Entity-manager write seam
**Path/Symbol:** `packages/core/database/src/entity-manager/index.ts:create` (332–373), `update` (424–477), `delete` (504–541).
**Signature:** `async create(uid: string, params: { data, select?, populate?, filters? }): Promise<Row | null>` (same shape for update/delete with `where` required).
**Data Shape:** params `{ where, data, select, populate, filters }`; returns the fully re-read entity or `null` when the where clause matched nothing.

### Decisive source
```ts
const states = await db.lifecycles.run('beforeCreate', uid, { params });
...
const res = await this.createQueryBuilder(uid)
  .insert(dataToInsert)
  .execute<Array<ID | { id: ID }>>();
const id = isRecord(res[0]) ? res[0].id : res[0];

const trx = await strapi.db.transaction();
try {
  await this.attachRelations(uid, id, data, { transaction: trx.get() });
  await trx.commit();
} catch (e) {
  await trx.rollback();
  await this.createQueryBuilder(uid).where({ id }).delete().execute(); // compensating delete
  throw e;
}

const result = await this.findOne(uid, { where: { id }, select: params.select, ... });
await db.lifecycles.run('afterCreate', uid, { params, result }, states);
```
Update mirrors this: read entity first (`return null` if absent), update by id only if `dataToUpdate` non-empty, then relation transaction whose catch **reverts the row to the previously read entity**: `.update(entity).execute()`. Delete reads first (`findOne`, `['id'].concat(select)`), deletes the row, then deletes relations in a transaction with plain rollback (row already gone — no compensation possible).

**Flow:** before\* lifecycles (States Map returned) → validate/defaults via `processData(metadata, data, { withDefaults })` → main-row SQL → relations in own transaction → on failure compensate (create: delete inserted row; update: restore prior row snapshot) → re-read via findOne → after\* lifecycles with the same States Map.
**Invariant:** The States Map from `run('before*')` must be passed as 4th arg to `run('after*')`; compensation must use the same `createQueryBuilder(uid).where({ id })` targeting so orphan rows never persist; empty `where` throws before any SQL runs (`'Update requires a where parameter'` / `'Delete requires a where parameter'`).
**Probe:** `packages/core/database/src/__tests__/lifecycles.test.ts` — "use shared state" pins that state set in a `beforeCreate` subscriber arrives intact in `afterCreate` through the returned Map.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "create query builder entity manager", file_pattern: "packages/core/database/src/entity-manager/*", limit: 30 });
```
Executed during pass 1: 86 total matches led by `createQueryBuilder` (1792–1794), `entity-repository.create`, `create` (332–373).

## Verdict
Adopt the three-part discipline: (1) lifecycle phases bracket every mutation with an explicit state channel, (2) relations mutate in a separate short transaction, (3) failure triggers a *compensating action* appropriate to the operation (delete inserted row / restore prior snapshot / nothing for delete). Adapt transaction primitives to your host (knex trx here). Omit Strapi's TODO semantics around findOne-triggered lifecycles. Coverage: `no_recorded_issue` + `metadata_match` for `entity-manager/index.ts`.
