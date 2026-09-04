<!-- capsule-v2 -->
# User display-name substitution — how do filters and sorts read comma-delimited user IDs as visible names (and why is the roster pre-filtered in JS)?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does like/nlike against a User column match display names when storage is user IDs, and how do PG/SQLite swap the substitution primitive?

## UserGeneralHandler filterLikeNlike + buildDisplayNameExpression
**Path/Symbol:** `packages/nocodb/src/db/field-handler/handlers/user/user.general.handler.ts` — like/nlike rewire :27-30; applySort :65-90; parseUserInput :116-290; filterLikeNlike :292-359; replaceDelimitedWithKeyValue :361-372. Dialect twins `user.pg.handler.ts` / `user.sqlite.handler.ts` (:13-22 both) override the primitive via DBQueryClient composition shells.
**Signature:** `replaceDelimitedWithKeyValue({knex, needleColumn, stack}) → string` — folds `REPLACE(acc, key, value)` over the roster producing raw SQL text.
**Data Shape:** Storage: single = one id; multi = comma-delimited ids. Roster via `BaseUser.getUsersList(context, {base_id, include_internal_user:true})`; input validation adds `include_ws_deleted: true` ("deleted user may still exist on some fields — still valid as a historical record").

### Decisive source
```ts
// :243-250 — empty value skips substitution entirely:
// Empty value (fresh filter row): skip the display-name substitution —
// the generic handler's empty-value semantics apply to the raw column.
// :251-279 — JS-side PRE-FILTER decides WHICH users get REPLACE arms:
const users = baseUsers.filter((user) => {
  const filterVal = val.toLowerCase();
  const displayValue = (user.display_name || user.email || '').toLowerCase();
  if (filterVal.startsWith('%') && filterVal.endsWith('%'))
    return displayValue.includes(filterVal.substring(1, -1...));
  ... // anchored %foo / foo% become endsWith/startsWith JS predicates
});
// then only matching users are folded into SQL:
return this.singleLineTextHandler.filterLike(
  { val, sourceField: knex.raw(finalStatement) }, rootArgs, options);
```

**Flow:** filter() first resolves `{currentUser}` placeholders via handleCurrentUserFilter → like/nlike with a real value pre-filter the roster in JS by wildcard semantics → fold ONLY matches into nested REPLACE over sourceField → delegate to SingleLineText's like/nlike with the rewritten sourceField → sort uses the FULL roster (no pre-filter) so ordering sees every id.
**Invariant:** (1) The JS pre-filter is a performance AND correctness device: folding all users would make every id replace to its name and the LIKE would then compare names — but folding none keeps ids, breaking matches; the wildcard-aware subset preserves both. (2) applySort resolves CreatedBy/LastModifiedBy column names via getColumnName into a LOCAL and never mutates the shared cached Column (:96-99 comment). (3) Duplicate-user input is rejected (`Set size !== length`) and multi/single arity enforced at parseUserInput. (4) PG/SQLite handlers are composition shells: UserPgHandler extends GenericPgFieldHandler but delegates ALL user methods to an inner UserLikeNLikePgHandler whose singleLineTextHandler is the PG generic — inheriting ilike/::text while swapping the REPLACE primitive for `replace_delimited_with_keyvalue`.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "skip the display-name substitution" (:243); search_graph resolves `UserGeneralHandler.replaceDelimitedWithKeyValue Method` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "filterLikeNlike", limit: 5 });
```

## Verdict
Adopt pre-filter-then-fold substitution + dialect-primitive injection; adapt roster query; omit the O(values×users) find-scan history (now Map-indexed). Caveat: no direct tests at pin.
