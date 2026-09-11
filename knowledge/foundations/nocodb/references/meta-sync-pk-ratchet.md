<!-- capsule-v2 -->
# PK ratchet — how can a user flag a column as primary key when the external DB says UNIQUE NOT NULL, and survive the next sync?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do you let users repair a no-PK external table by hand-flagging pk in the UI, without the next meta-sync erasing their fix?

## pk-preservation helpers
**Path/Symbol:** `packages/nocodb/src/services/meta-diffs/pk-preservation.ts` — `isPkRegression` (:34-39), `detectColumnSchemaPropsChanged` (:51-65), `resolvePkAfterSync` (:71-76); consumers: meta-diffs.service.ts :312 (detect) and :1058 (apply).
**Signature:** `isPkRegression(noCoDbPk, dbPk): boolean` = `!!noCoDbPk && !dbPk`; `resolvePkAfterSync(noCoDbPk, dbPk): boolean` = `!!(dbPk || noCoDbPk)`.
**Data Shape:** Operates ONLY on physical schema props `{pk, rqd, un, ai, unique}` — never NocoDB-only metadata (title/description/uidt). All comparisons coerce through `!!`.

### Decisive source
```ts
/**
 * Customers can recover from external schemas that declare uniqueness via
 * `UNIQUE NOT NULL` instead of `PRIMARY KEY` (the no-PK family of read /
 * delete / link-create crashes) by manually flagging the `id` column as PK
 * in NocoDB. To make that flip durable, the diff is asymmetric on `pk`:
 *
 *   - `pk` *gained* on the DB side: propagate to NocoDB.
 *   - `pk` *lost* on the DB side while NocoDB has it: keep NocoDB's value.
 */
export function detectColumnSchemaPropsChanged(oldCol: ColumnSchemaProps, dbCol: ColumnSchemaProps): boolean {
  const pkChanged = !!oldCol.pk !== !!dbCol.pk && !isPkRegression(oldCol.pk, dbCol.pk);
  return (
    pkChanged ||
    !!oldCol.rqd !== !!dbCol.rqd ||
    !!oldCol.un !== !!dbCol.un ||
    !!oldCol.ai !== !!dbCol.ai ||
    !!oldCol.unique !== !!dbCol.unique
  );
}
/** Returns the `pk` value to write back to NocoDB after a sync diff fires.
 *  Acts as a ratchet — pk only goes from false to true, never back. */
export function resolvePkAfterSync(noCoDbPk, dbPk): boolean {
  return !!(dbPk || noCoDbPk);
}
```

**Flow:** getMetaDiff calls detectColumnSchemaPropsChanged(oldCol, dbCol) ⇒ fires TABLE_COLUMN_PROPS_CHANGED only when a prop genuinely flips AND the pk flip is not a regression → syncBaseMeta's apply case re-introspects, then writes `{pk: resolvePkAfterSync(change.column.pk, colMeta.pk), ai, rqd, un, unique}` — the ratchet ORs the user's flag back in.
**Invariant:** Asymmetry is the whole contract: symmetric comparison would fire PROPS_CHANGED on every sync after a manual pk flag, and the apply would clear it — an infinite user-visible revert loop. The other four props stay SYMMETRIC on purpose (they mirror the DB). Module doc names its own test file (`tests/unit/helpersTest/pkPreservation.test.ts`) which does NOT exist at this inspo pin (tests/unit absent; SQL fixtures only) — treat as upstream-only coverage caveat.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `resolvePkAfterSync` Function :71-76 exactly; grep confirms `isPkRegression` has exactly one consumer (the pkChanged line inside detectColumnSchemaPropsChanged).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "resolvePkAfterSync isPkRegression detectColumnSchemaPropsChanged", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-way ratchet for ANY user-overridable property that mirrors an external source of truth: diff asymmetrically (skip "regressions"), write with OR-fusion. Adapt the prop set to your schema vocabulary. Omit nothing else — the brevity IS the design (76 lines including docs).
