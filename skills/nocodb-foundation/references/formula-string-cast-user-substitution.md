<!-- capsule-v2 -->
# formula STRING cast wrapper — how does a node's `.cast` annotation become a synthetic STRING() call, and where do user emails get substituted into SQL?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does the compiler force string context onto an arbitrary subtree, and what is the exact SQL shape of the lazy User/CreatedBy/LastModifiedBy email substitution builder?

## pt.cast STRING re-dispatch + User-family REPLACE chain
**Path/Symbol:** `packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts:_formulaQueryBuilder.fn` (:376–398) and the UITypes.User/CreatedBy/LastModifiedBy registry arm (:263–308); primitive `DBQueryClient.replaceDelimitedWithKeyValue` via `src/helpers/dbHelpers.getColumnName` (:279).
**Signature:** `(pt: FnParsedTreeNode, prevBinaryOp?) => Promise<{builder}>`; user arm: `async () => { builder: knex.raw(finalStatement).wrap('(', ')') }`.
**Data Shape:** synthetic re-dispatch node `{type: CallExpression, arguments: [{...pt, cast: null}], callee: {type:'Identifier', name:'STRING'}}`; user roster `(Partial<User> & BaseUser)[]` memoized on the closure (`baseUsers = baseUsers ?? await BaseUser.getUsersList(context, {base_id, include_internal_user:true})`).

### Decisive source
```ts
// :377–398 — cast is stripped from the CLONE only; dispatch order matters (cast BEFORE CallExpression)
if (pt.type === JSEPNode.CALL_EXP) {
  pt.arguments?.forEach?.((arg) => {
    if (arg.fnName) return;                    // idempotence: never overwrite an inherited fnName
    arg.fnName = pt.callee.name.toUpperCase();
    arg.argsCount = pt.arguments?.length;
  });
}
if (pt.cast === FormulaDataTypes.STRING) {
  return fn(
    { type: JSEPNode.CALL_EXP,
      arguments: [{ ...pt, cast: null }],      // clone with cast cleared → recursion terminates
      callee: { type: 'Identifier', name: 'STRING' } },
    prevBinaryOp,
  );
}
```
```ts
// :282–301 — two SQL shapes keyed by client family (pg/sqlite vs everyone else)
if (knex.clientType() === 'pg' || knex.clientType() === 'sqlite3') {
  finalStatement = `(${DBQueryClient.get(knex.clientType()).replaceDelimitedWithKeyValue({
    knex, needleColumn: columnName,
    stack: baseUsers.map((user) => ({ key: user.id, value: `${user.email}` })),
  })})`;
} else {
  finalStatement = baseUsers.reduce((acc, user) => {
    const qb = knex.raw(`REPLACE(${acc}, ?, ?)`, [user.id, user.email]);
    return qb.toQuery();
  }, knex.raw(`??`, [columnName]).toQuery());
}
```

**Flow:** every `fn()` entry first stamps unvisited CallExpression arguments with their parent's uppercased callee name + arity (guarded by `if (arg.fnName) return`, so nested calls keep their OWN name and re-visits are no-ops). Then a node carrying `pt.cast === STRING` never compiles itself: it re-enters `fn` as argument #1 of a synthetic `STRING()` call with `cast: null` on the clone — one wrapper per annotated node, terminating because only the clone loses the annotation while the original subtree is untouched. The User-family registry arm builds lazily and memoizes the roster fetch in the closure variable `baseUsers` (shared across all user columns of this compilation): it resolves the storage column through `getColumnName` because system=false CreatedBy/LastModifiedBy have no column_name of their own (siblings supply it), then renders dialect-shaped substitution — pg/sqlite delegate to `replaceDelimitedWithKeyValue` (delimited-token replace over the id column), mysql-family/mssql/oracle fold nested `REPLACE(REPLACE(col, id1, email1), id2, email2)` by reducing raw builders to query strings.
**Invariant:** (1) The synthetic STRING call must carry `cast: null` ON THE ARGUMENT CLONE — re-dispatching with the original node loops forever. (2) Cast handling runs BEFORE the CallExpression branch so a STRING-cast function call wraps the whole rendered function. (3) The `fnName` stamp guard makes stamping idempotent AND preserves inner-call names — dropping the guard lets outer functions rename inner aggregates and corrupts thunk resolution. (4) The non-pg/sqlite reduce MUST materialize each intermediate with `.toQuery()` before nesting — composing raws without materialization produces nested-builder binding corruption; the pg/sqlite path avoids the ladder entirely via the delimited-replace primitive. (5) Roster memoization is per-compilation (closure), not global — a porter caching it at module scope serves stale emails across bases.
**Probe:** `grep -n "cast === FormulaDataTypes.STRING" packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts` → exactly :386; `grep -n "replaceDelimitedWithKeyValue" packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts` → exactly :285. Runner BLOCKED (no upstream unit tests cover db/formulav2) → line-anchored deterministic checks.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "FormulaDataTypes.STRING cast BaseUser getUsersList REPLACE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the clone-with-cast-null re-dispatch, the idempotent fnName stamp, and lazy memoized roster with sibling-column resolution; adapt the two SQL shapes to host dialect families; omit DBQueryClient/NestJS wiring specifics.
